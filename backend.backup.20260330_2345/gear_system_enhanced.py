#!/usr/bin/env python3
"""
增强型齿轮执行系统 (Enhanced Gear Execution System)

核心特性:
1. 所有任务必须经过审核才能执行
2. 执行前强制检查审核状态
3. 未审核任务自动转入审核队列
"""

import os
import sys
import json
import sqlite3
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 数据库路径
DB_PATH = os.path.expanduser('/opt/kanban-react/backend/kanban_v5.db')


class TaskAuditStatus(Enum):
    """任务审核状态"""
    PENDING = "pending"       # 待审核
    APPROVED = "approved"     # 已通过
    REJECTED = "rejected"     # 已拒绝
    EXECUTING = "executing"   # 执行中
    COMPLETED = "completed"   # 已完成
    FAILED = "failed"         # 执行失败


class GearExecutionManager:
    """齿轮执行管理器 - 带审核控制"""
    
    def __init__(self):
        self.db_path = DB_PATH
    
    def get_db(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        
        return conn
    
    def check_task_audit_status(self, task_id: int) -> Dict[str, Any]:
        """
        检查任务审核状态
        
        Returns:
            {
                'can_execute': bool,
                'status': str,
                'message': str,
                'audit_record': dict or None
            }
        """
        conn = self.get_db()
        c = conn.cursor()
        
        try:
            # 1. 检查任务是否存在
            c.execute('''
                SELECT id, title, status, requires_audit, audit_status 
                FROM tasks 
                WHERE id = ?
            ''', (task_id,))
            task = c.fetchone()
            
            if not task:
                return {
                    'can_execute': False,
                    'status': 'not_found',
                    'message': f'任务 {task_id} 不存在',
                    'audit_record': None
                }
            
            task_dict = dict(task)
            
            # 2. 检查任务是否需要审核
            requires_audit = task_dict.get('requires_audit', 1)  # 默认需要审核
            audit_status = task_dict.get('audit_status', 'pending')
            
            if not requires_audit:
                return {
                    'can_execute': True,
                    'status': 'no_audit_required',
                    'message': '该任务不需要审核',
                    'audit_record': None
                }
            
            # 3. 检查审核状态
            if audit_status == TaskAuditStatus.APPROVED.value:
                return {
                    'can_execute': True,
                    'status': 'approved',
                    'message': '审核已通过，可以执行',
                    'audit_record': self._get_audit_record(c, task_id)
                }
            elif audit_status == TaskAuditStatus.REJECTED.value:
                return {
                    'can_execute': False,
                    'status': 'rejected',
                    'message': '任务已被拒绝，无法执行',
                    'audit_record': self._get_audit_record(c, task_id)
                }
            elif audit_status == TaskAuditStatus.PENDING.value:
                # 检查是否已在审核队列
                audit_record = self._get_audit_record(c, task_id)
                if audit_record:
                    return {
                        'can_execute': False,
                        'status': 'pending_review',
                        'message': '任务正在审核中，请等待审核完成',
                        'audit_record': audit_record
                    }
                else:
                    # 自动创建审核任务
                    self._create_audit_task(conn, c, task_id, task_dict['title'])
                    return {
                        'can_execute': False,
                        'status': 'audit_created',
                        'message': '任务已提交审核，等待审核通过后才能执行',
                        'audit_record': None
                    }
            else:
                return {
                    'can_execute': False,
                    'status': audit_status,
                    'message': f'任务状态为 {audit_status}，无法执行',
                    'audit_record': None
                }
                
        finally:
            conn.close()
    
    def _get_audit_record(self, cursor, task_id: int) -> Optional[Dict]:
        """获取任务的审核记录"""
        cursor.execute('''
            SELECT id, task_type, title, description, status, 
                   notes, created_at, completed_at, reviewer
            FROM manual_review_tasks 
            WHERE source_id = ? AND task_type = 'task_execution'
            ORDER BY created_at DESC 
            LIMIT 1
        ''', (task_id,))
        
        row = cursor.fetchone()
        return dict(row) if row else None
    
    def _create_audit_task(self, conn, cursor, task_id: int, task_title: str):
        """创建审核任务"""
        try:
            cursor.execute('''
                INSERT INTO manual_review_tasks 
                (task_type, title, description, source, source_id, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
            ''', (
                'task_execution',
                f'执行任务: {task_title}',
                f'任务ID: {task_id}\n任务名称: {task_title}\n\n该任务需要审核后才能执行。',
                'gear_system',
                task_id,
                'pending'
            ))
            
            # 更新任务的审核状态
            cursor.execute('''
                UPDATE tasks 
                SET audit_status = ?, updated_at = datetime('now')
                WHERE id = ?
            ''', (TaskAuditStatus.PENDING.value, task_id))
            
            conn.commit()
            logger.info(f"✅ 已为任务 {task_id} 创建审核请求")
            
        except Exception as e:
            logger.error(f"创建审核任务失败: {e}")
            raise
    
    def execute_gear(self, task_id: int, gear_name: str, 
                     execute_func, *args, **kwargs) -> Dict[str, Any]:
        """
        执行齿轮 - 带审核检查
        
        Args:
            task_id: 任务ID
            gear_name: 齿轮名称
            execute_func: 实际执行的函数
            
        Returns:
            执行结果
        """
        # 1. 检查审核状态
        audit_check = self.check_task_audit_status(task_id)
        
        if not audit_check['can_execute']:
            logger.warning(f"⛔ 任务 {task_id} 执行被拒绝: {audit_check['message']}")
            return {
                'success': False,
                'error': audit_check['message'],
                'audit_status': audit_check['status'],
                'requires_audit': True
            }
        
        # 2. 记录齿轮执行开始
        execution_id = self._record_gear_start(task_id, gear_name)
        
        try:
            # 3. 更新任务状态为执行中
            self._update_task_status(task_id, TaskAuditStatus.EXECUTING.value)
            
            # 4. 执行实际任务
            logger.info(f"⚙️ 开始执行齿轮 '{gear_name}' 对于任务 {task_id}")
            result = execute_func(*args, **kwargs)
            
            # 5. 记录成功
            self._record_gear_complete(execution_id, 'success', result)
            self._update_task_status(task_id, TaskAuditStatus.COMPLETED.value)
            
            logger.info(f"✅ 齿轮 '{gear_name}' 执行成功")
            return {
                'success': True,
                'result': result,
                'execution_id': execution_id
            }
            
        except Exception as e:
            # 6. 记录失败
            error_msg = str(e)
            self._record_gear_complete(execution_id, 'failed', {'error': error_msg})
            self._update_task_status(task_id, TaskAuditStatus.FAILED.value)
            
            logger.error(f"❌ 齿轮 '{gear_name}' 执行失败: {error_msg}")
            return {
                'success': False,
                'error': error_msg,
                'execution_id': execution_id
            }
    
    def _record_gear_start(self, task_id: int, gear_name: str) -> int:
        """记录齿轮执行开始"""
        conn = self.get_db()
        c = conn.cursor()
        
        try:
            c.execute('''
                INSERT INTO gear_executions 
                (task_id, gear_name, status, started_at)
                VALUES (?, ?, 'running', datetime('now'))
            ''', (task_id, gear_name))
            
            execution_id = c.lastrowid
            conn.commit()
            return execution_id
            
        finally:
            conn.close()
    
    def _record_gear_complete(self, execution_id: int, status: str, output: Dict):
        """记录齿轮执行完成"""
        conn = self.get_db()
        c = conn.cursor()
        
        try:
            c.execute('''
                UPDATE gear_executions 
                SET status = ?, output = ?, completed_at = datetime('now')
                WHERE id = ?
            ''', (status, json.dumps(output), execution_id))
            
            conn.commit()
            
        finally:
            conn.close()
    
    def _update_task_status(self, task_id: int, status: str):
        """更新任务状态"""
        conn = self.get_db()
        c = conn.cursor()
        
        try:
            c.execute('''
                UPDATE tasks 
                SET audit_status = ?, updated_at = datetime('now')
                WHERE id = ?
            ''', (status, task_id))
            
            conn.commit()
            
        finally:
            conn.close()
    
    def approve_task(self, task_id: int, reviewer: str = 'system', 
                     notes: str = '') -> Dict[str, Any]:
        """
        批准任务执行
        
        Args:
            task_id: 任务ID
            reviewer: 审核人
            notes: 审核备注
            
        Returns:
            审核结果
        """
        conn = self.get_db()
        c = conn.cursor()
        
        try:
            # 1. 更新任务审核状态
            c.execute('''
                UPDATE tasks 
                SET audit_status = ?, updated_at = datetime('now')
                WHERE id = ?
            ''', (TaskAuditStatus.APPROVED.value, task_id))
            
            # 2. 更新审核任务记录
            c.execute('''
                UPDATE manual_review_tasks 
                SET status = ?, reviewer = ?, notes = ?, completed_at = datetime('now')
                WHERE source_id = ? AND task_type = 'task_execution'
            ''', ('approved', reviewer, notes, task_id))
            
            conn.commit()
            
            logger.info(f"✅ 任务 {task_id} 已被 {reviewer} 批准")
            return {
                'success': True,
                'message': '任务已批准，可以执行',
                'task_id': task_id,
                'reviewer': reviewer
            }
            
        except Exception as e:
            logger.error(f"批准任务失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
            
        finally:
            conn.close()
    
    def reject_task(self, task_id: int, reviewer: str = 'system', 
                    reason: str = '') -> Dict[str, Any]:
        """
        拒绝任务执行
        
        Args:
            task_id: 任务ID
            reviewer: 审核人
            reason: 拒绝原因
            
        Returns:
            审核结果
        """
        conn = self.get_db()
        c = conn.cursor()
        
        try:
            # 1. 更新任务审核状态
            c.execute('''
                UPDATE tasks 
                SET audit_status = ?, updated_at = datetime('now')
                WHERE id = ?
            ''', (TaskAuditStatus.REJECTED.value, task_id))
            
            # 2. 更新审核任务记录
            c.execute('''
                UPDATE manual_review_tasks 
                SET status = ?, reviewer = ?, notes = ?, completed_at = datetime('now')
                WHERE source_id = ? AND task_type = 'task_execution'
            ''', ('rejected', reviewer, reason, task_id))
            
            conn.commit()
            
            logger.info(f"❌ 任务 {task_id} 已被 {reviewer} 拒绝")
            return {
                'success': True,
                'message': '任务已拒绝',
                'task_id': task_id,
                'reviewer': reviewer,
                'reason': reason
            }
            
        except Exception as e:
            logger.error(f"拒绝任务失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
            
        finally:
            conn.close()
    
    def get_pending_audits(self) -> List[Dict[str, Any]]:
        """获取所有待审核的任务"""
        conn = self.get_db()
        c = conn.cursor()
        
        try:
            c.execute('''
                SELECT 
                    t.id as task_id,
                    t.title as task_title,
                    t.status as task_status,
                    t.audit_status,
                    t.created_at as task_created_at,
                    m.id as audit_id,
                    m.title as audit_title,
                    m.description as audit_description,
                    m.created_at as audit_created_at
                FROM tasks t
                JOIN manual_review_tasks m ON t.id = m.source_id
                WHERE t.audit_status = 'pending' 
                   OR m.status = 'pending'
                ORDER BY m.created_at DESC
            ''')
            
            audits = [dict(row) for row in c.fetchall()]
            return audits
            
        finally:
            conn.close()


# 全局实例
gear_manager = GearExecutionManager()


def execute_with_audit(task_id: int, gear_name: str, 
                       execute_func, *args, **kwargs) -> Dict[str, Any]:
    """
    带审核的齿轮执行函数
    
    这是主要的对外接口
    """
    return gear_manager.execute_gear(task_id, gear_name, execute_func, *args, **kwargs)


def check_audit_status(task_id: int) -> Dict[str, Any]:
    """检查任务审核状态"""
    return gear_manager.check_task_audit_status(task_id)


def approve_task_execution(task_id: int, reviewer: str = 'system', 
                           notes: str = '') -> Dict[str, Any]:
    """批准任务执行"""
    return gear_manager.approve_task(task_id, reviewer, notes)


def reject_task_execution(task_id: int, reviewer: str = 'system', 
                          reason: str = '') -> Dict[str, Any]:
    """拒绝任务执行"""
    return gear_manager.reject_task(task_id, reviewer, reason)


if __name__ == '__main__':
    # 测试代码
    print("=" * 60)
    print("增强型齿轮执行系统测试")
    print("=" * 60)
    
    # 测试获取待审核任务
    pending = gear_manager.get_pending_audits()
    print(f"\n📋 待审核任务数量: {len(pending)}")
    
    for audit in pending[:5]:
        print(f"  - [{audit['audit_id']}] {audit['task_title']}")
