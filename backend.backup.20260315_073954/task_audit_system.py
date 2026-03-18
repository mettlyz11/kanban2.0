#!/usr/bin/env python3
"""
任务生成审核系统 (Task Generation Audit System)

统一处理所有自动生成的任务审核:
1. 齿轮系统 (Gear System)
2. 战略协调员 (Strategy Coordinator / Long Thinking)
3. 感知Agent (Perception Agent)
4. Cron定时任务

所有任务必须经过人工审核后才能执行
"""

import os
import sys
import json
import sqlite3
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_PATH = os.path.expanduser('/opt/kanban-react/backend/kanban_v5.db')


class TaskSource(Enum):
    """任务来源"""
    GEAR_SYSTEM = "gear_system"           # 齿轮系统
    STRATEGY_COORDINATOR = "strategy_coordinator"  # 战略协调员
    LONG_THINKING = "long_thinking"       # 长思考系统
    PERCEPTION_AGENT = "perception_agent" # 感知Agent
    CRON_TASK = "cron_task"               # Cron定时任务
    MANUAL = "manual"                     # 手动创建


class TaskAuditSystem:
    """
    任务生成审核系统
    
    核心功能:
    1. 拦截所有自动生成的任务
    2. 强制创建审核记录
    3. 管理审核状态
    4. 阻止未审核任务的执行
    """
    
    def __init__(self):
        self.db_path = DB_PATH
        self.stats = {
            'tasks_generated': 0,
            'tasks_blocked': 0,
            'tasks_approved': 0,
            'tasks_rejected': 0
        }
    
    def get_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def register_task_generation(self, 
                                  title: str,
                                  description: str,
                                  source: TaskSource,
                                  priority: str = 'medium',
                                  source_id: Optional[int] = None,
                                  project_id: Optional[int] = None,
                                  suggested_action: str = '') -> Dict[str, Any]:
        """
        注册任务生成 - 所有生成的任务必须通过此接口
        
        Args:
            title: 任务标题
            description: 任务描述
            source: 任务来源
            priority: 优先级
            source_id: 来源ID
            project_id: 项目ID
            suggested_action: 建议操作
            
        Returns:
            {
                'success': bool,
                'task_id': int or None,
                'audit_id': int or None,
                'status': str,
                'message': str
            }
        """
        conn = self.get_db()
        c = conn.cursor()
        
        try:
            # 1. 生成任务编号
            c.execute("SELECT COUNT(*) FROM tasks")
            count = c.fetchone()[0] + 1
            number = f"AUD{count:03d}"
            
            # 2. 创建任务 - 强制需要审核
            c.execute('''
                INSERT INTO tasks 
                (number, title, description, status, priority, 
                 project_id, requires_audit, audit_status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, 1, 'pending', datetime('now'), datetime('now'))
            ''', (
                number,
                title,
                f"【来源: {source.value}】\n{description}\n\n⚠️ 此任务需要人工审核后才能执行",
                'todo',
                priority,
                project_id
            ))
            
            task_id = c.lastrowid
            
            # 3. 创建审核任务
            c.execute('''
                INSERT INTO manual_review_tasks 
                (task_type, title, description, source, source_id, 
                 status, priority, created_at)
                VALUES (?, ?, ?, ?, ?, 'pending', ?, datetime('now'))
            ''', (
                source.value,
                f'审核: {title}',
                f'''任务来源: {source.value}
任务ID: {task_id}
任务编号: {number}
优先级: {priority}
建议操作: {suggested_action}

详细描述:
{description}

---
请审核此任务:
1. 是否必要？
2. 资源是否充足？
3. 风险是否可控？
4. 预期收益是否明确？''',
                source.value,
                task_id,
                priority
            ))
            
            audit_id = c.lastrowid
            conn.commit()
            
            self.stats['tasks_generated'] += 1
            
            logger.info(f"✅ 已注册任务 {number} (来源: {source.value}) 并提交审核")
            
            return {
                'success': True,
                'task_id': task_id,
                'audit_id': audit_id,
                'task_number': number,
                'status': 'pending_audit',
                'message': '任务已创建并提交审核，需要人工审核后才能执行'
            }
            
        except Exception as e:
            logger.error(f"❌ 任务注册失败: {e}")
            conn.rollback()
            return {
                'success': False,
                'task_id': None,
                'audit_id': None,
                'status': 'error',
                'message': f'任务注册失败: {str(e)}'
            }
            
        finally:
            conn.close()
    
    def approve_task(self, audit_id: int, reviewer: str, 
                     notes: str = '') -> Dict[str, Any]:
        """
        批准任务
        
        Args:
            audit_id: 审核任务ID
            reviewer: 审核人
            notes: 审核备注
        """
        conn = self.get_db()
        c = conn.cursor()
        
        try:
            # 获取关联的任务ID
            c.execute('SELECT source_id FROM manual_review_tasks WHERE id = ?', (audit_id,))
            row = c.fetchone()
            if not row:
                return {
                    'success': False,
                    'message': '审核任务不存在'
                }
            
            task_id = row[0]
            
            # 更新审核任务状态
            c.execute('''
                UPDATE manual_review_tasks 
                SET status = 'approved', reviewer = ?, notes = ?, 
                    completed_at = datetime('now')
                WHERE id = ?
            ''', (reviewer, notes, audit_id))
            
            # 更新任务状态
            c.execute('''
                UPDATE tasks 
                SET audit_status = 'approved', updated_at = datetime('now')
                WHERE id = ?
            ''', (task_id,))
            
            conn.commit()
            
            self.stats['tasks_approved'] += 1
            
            logger.info(f"✅ 任务 {task_id} 已被 {reviewer} 批准")
            
            return {
                'success': True,
                'task_id': task_id,
                'audit_id': audit_id,
                'reviewer': reviewer,
                'message': '任务已批准，可以执行'
            }
            
        except Exception as e:
            logger.error(f"批准任务失败: {e}")
            return {
                'success': False,
                'message': f'批准失败: {str(e)}'
            }
            
        finally:
            conn.close()
    
    def reject_task(self, audit_id: int, reviewer: str, 
                    reason: str = '') -> Dict[str, Any]:
        """
        拒绝任务
        
        Args:
            audit_id: 审核任务ID
            reviewer: 审核人
            reason: 拒绝原因
        """
        conn = self.get_db()
        c = conn.cursor()
        
        try:
            # 获取关联的任务ID
            c.execute('SELECT source_id FROM manual_review_tasks WHERE id = ?', (audit_id,))
            row = c.fetchone()
            if not row:
                return {
                    'success': False,
                    'message': '审核任务不存在'
                }
            
            task_id = row[0]
            
            # 更新审核任务状态
            c.execute('''
                UPDATE manual_review_tasks 
                SET status = 'rejected', reviewer = ?, notes = ?, 
                    completed_at = datetime('now')
                WHERE id = ?
            ''', (reviewer, reason, audit_id))
            
            # 更新任务状态
            c.execute('''
                UPDATE tasks 
                SET audit_status = 'rejected', status = 'cancelled', 
                    updated_at = datetime('now')
                WHERE id = ?
            ''', (task_id,))
            
            conn.commit()
            
            self.stats['tasks_rejected'] += 1
            
            logger.info(f"❌ 任务 {task_id} 已被 {reviewer} 拒绝")
            
            return {
                'success': True,
                'task_id': task_id,
                'audit_id': audit_id,
                'reviewer': reviewer,
                'message': '任务已拒绝'
            }
            
        except Exception as e:
            logger.error(f"拒绝任务失败: {e}")
            return {
                'success': False,
                'message': f'拒绝失败: {str(e)}'
            }
            
        finally:
            conn.close()
    
    def check_before_execution(self, task_id: int) -> Dict[str, Any]:
        """
        执行前检查 - 阻止未审核任务的执行
        
        Returns:
            {
                'can_execute': bool,
                'status': str,
                'message': str
            }
        """
        conn = self.get_db()
        c = conn.cursor()
        
        try:
            # 查询任务
            c.execute('''
                SELECT id, title, requires_audit, audit_status 
                FROM tasks 
                WHERE id = ?
            ''', (task_id,))
            
            row = c.fetchone()
            if not row:
                self.stats['tasks_blocked'] += 1
                return {
                    'can_execute': False,
                    'status': 'not_found',
                    'message': '任务不存在'
                }
            
            task = dict(row)
            
            # 如果不需要审核
            if not task.get('requires_audit'):
                return {
                    'can_execute': True,
                    'status': 'no_audit_required',
                    'message': '任务不需要审核'
                }
            
            # 检查审核状态
            audit_status = task.get('audit_status', 'pending')
            
            if audit_status == 'approved':
                return {
                    'can_execute': True,
                    'status': 'approved',
                    'message': '审核已通过'
                }
            elif audit_status == 'rejected':
                self.stats['tasks_blocked'] += 1
                return {
                    'can_execute': False,
                    'status': 'rejected',
                    'message': '任务已被拒绝，无法执行'
                }
            else:  # pending
                self.stats['tasks_blocked'] += 1
                return {
                    'can_execute': False,
                    'status': 'pending',
                    'message': '任务待审核，请先审核后再执行'
                }
                
        finally:
            conn.close()
    
    def get_pending_audits(self, source: Optional[TaskSource] = None) -> List[Dict[str, Any]]:
        """获取待审核任务列表"""
        conn = self.get_db()
        c = conn.cursor()
        
        try:
            if source:
                c.execute('''
                    SELECT 
                        m.id as audit_id,
                        m.task_type,
                        m.title,
                        m.description,
                        m.priority,
                        m.created_at,
                        t.id as task_id,
                        t.number as task_number
                    FROM manual_review_tasks m
                    JOIN tasks t ON m.source_id = t.id
                    WHERE m.status = 'pending' AND m.task_type = ?
                    ORDER BY 
                        CASE m.priority 
                            WHEN 'high' THEN 1 
                            WHEN 'medium' THEN 2 
                            ELSE 3 
                        END,
                        m.created_at ASC
                ''', (source.value,))
            else:
                c.execute('''
                    SELECT 
                        m.id as audit_id,
                        m.task_type,
                        m.title,
                        m.description,
                        m.priority,
                        m.created_at,
                        t.id as task_id,
                        t.number as task_number
                    FROM manual_review_tasks m
                    JOIN tasks t ON m.source_id = t.id
                    WHERE m.status = 'pending'
                    ORDER BY 
                        CASE m.priority 
                            WHEN 'high' THEN 1 
                            WHEN 'medium' THEN 2 
                            ELSE 3 
                        END,
                        m.created_at ASC
                ''')
            
            audits = [dict(row) for row in c.fetchall()]
            return audits
            
        finally:
            conn.close()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        conn = self.get_db()
        c = conn.cursor()
        
        try:
            # 总体统计
            c.execute('''
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending,
                    SUM(CASE WHEN status = 'approved' THEN 1 ELSE 0 END) as approved,
                    SUM(CASE WHEN status = 'rejected' THEN 1 ELSE 0 END) as rejected
                FROM manual_review_tasks
            ''')
            
            row = c.fetchone()
            stats = dict(row) if row else {}
            
            # 按来源统计
            c.execute('''
                SELECT task_type, COUNT(*) as count
                FROM manual_review_tasks
                GROUP BY task_type
            ''')
            
            by_source = {row[0]: row[1] for row in c.fetchall()}
            
            return {
                'total': stats.get('total', 0),
                'pending': stats.get('pending', 0),
                'approved': stats.get('approved', 0),
                'rejected': stats.get('rejected', 0),
                'by_source': by_source,
                'system_stats': self.stats
            }
            
        finally:
            conn.close()


# 全局实例
task_audit_system = TaskAuditSystem()


def register_gear_task(title: str, description: str, priority: str = 'medium',
                       **kwargs) -> Dict[str, Any]:
    """注册齿轮系统任务"""
    return task_audit_system.register_task_generation(
        title=title,
        description=description,
        source=TaskSource.GEAR_SYSTEM,
        priority=priority,
        **kwargs
    )


def register_strategy_task(title: str, description: str, priority: str = 'medium',
                           **kwargs) -> Dict[str, Any]:
    """注册战略协调员任务"""
    return task_audit_system.register_task_generation(
        title=title,
        description=description,
        source=TaskSource.STRATEGY_COORDINATOR,
        priority=priority,
        **kwargs
    )


def register_long_thinking_task(title: str, description: str, priority: str = 'medium',
                                **kwargs) -> Dict[str, Any]:
    """注册长思考系统任务"""
    return task_audit_system.register_task_generation(
        title=title,
        description=description,
        source=TaskSource.LONG_THINKING,
        priority=priority,
        **kwargs
    )


def check_task_before_execution(task_id: int) -> Dict[str, Any]:
    """执行前检查"""
    return task_audit_system.check_before_execution(task_id)


def approve_task(audit_id: int, reviewer: str, notes: str = '') -> Dict[str, Any]:
    """批准任务"""
    return task_audit_system.approve_task(audit_id, reviewer, notes)


def reject_task(audit_id: int, reviewer: str, reason: str = '') -> Dict[str, Any]:
    """拒绝任务"""
    return task_audit_system.reject_task(audit_id, reviewer, reason)


if __name__ == '__main__':
    print("=" * 60)
    print("任务生成审核系统")
    print("=" * 60)
    
    # 测试注册任务
    print("\n📝 测试注册齿轮系统任务...")
    result = register_gear_task(
        title="测试齿轮任务",
        description="这是一个测试任务",
        priority="high"
    )
    print(f"结果: {result}")
    
    print("\n📝 测试注册战略协调员任务...")
    result = register_strategy_task(
        title="测试战略任务",
        description="这是一个战略任务",
        priority="medium"
    )
    print(f"结果: {result}")
    
    # 获取统计
    print("\n📊 统计信息:")
    stats = task_audit_system.get_stats()
    print(json.dumps(stats, indent=2, ensure_ascii=False))
