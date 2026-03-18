#!/usr/bin/env python3
"""
增强型监督系统 (Enhanced Supervisor System)

核心特性:
1. 监控所有任务的审核状态
2. 阻止未审核任务的执行
3. 自动提醒待审核任务
4. 生成审核报告
"""

import os
import sys
import json
import sqlite3
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 数据库路径
DB_PATH = os.path.expanduser('/opt/kanban-react/backend/kanban_v5.db')


@dataclass
class AuditReport:
    """审核报告"""
    report_time: str
    total_tasks: int
    pending_audit: int
    approved: int
    rejected: int
    executing: int
    completed: int
    failed: int
    avg_audit_time_hours: float
    critical_tasks: List[Dict[str, Any]]
    recommendations: List[str]


class SupervisorSystem:
    """监督系统 - 确保所有任务都经过审核"""
    
    def __init__(self):
        self.db_path = DB_PATH
        self.stats = {
            'tasks_checked': 0,
            'blocked_executions': 0,
            'audit_requests_created': 0
        }
    
    def get_db(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def enforce_audit_policy(self, task_id: int) -> Dict[str, Any]:
        """
        强制执行审核策略
        
        在任务执行前调用，确保任务已经过审核
        
        Returns:
            {
                'allowed': bool,
                'action': str,  # 'execute', 'block', 'create_audit'
                'message': str,
                'audit_status': str
            }
        """
        conn = self.get_db()
        c = conn.cursor()
        
        try:
            # 1. 查询任务审核状态
            c.execute('''
                SELECT id, title, audit_status, requires_audit, priority
                FROM tasks 
                WHERE id = ?
            ''', (task_id,))
            
            task = c.fetchone()
            if not task:
                self.stats['blocked_executions'] += 1
                return {
                    'allowed': False,
                    'action': 'block',
                    'message': f'任务 {task_id} 不存在',
                    'audit_status': 'not_found'
                }
            
            task_dict = dict(task)
            audit_status = task_dict.get('audit_status', 'pending')
            requires_audit = task_dict.get('requires_audit', 1)
            
            self.stats['tasks_checked'] += 1
            
            # 2. 如果不需要审核，允许执行
            if not requires_audit:
                return {
                    'allowed': True,
                    'action': 'execute',
                    'message': '任务不需要审核',
                    'audit_status': 'not_required'
                }
            
            # 3. 根据审核状态决定
            if audit_status == 'approved':
                return {
                    'allowed': True,
                    'action': 'execute',
                    'message': '审核已通过，允许执行',
                    'audit_status': 'approved'
                }
            
            elif audit_status == 'rejected':
                self.stats['blocked_executions'] += 1
                return {
                    'allowed': False,
                    'action': 'block',
                    'message': '任务已被拒绝，无法执行',
                    'audit_status': 'rejected'
                }
            
            elif audit_status in ['pending', None]:
                # 检查是否已有审核任务
                c.execute('''
                    SELECT id, status 
                    FROM manual_review_tasks 
                    WHERE source_id = ? AND task_type = 'task_execution'
                    ORDER BY created_at DESC 
                    LIMIT 1
                ''', (task_id,))
                
                audit_task = c.fetchone()
                
                if audit_task:
                    audit_dict = dict(audit_task)
                    self.stats['blocked_executions'] += 1
                    return {
                        'allowed': False,
                        'action': 'block',
                        'message': f'任务正在审核中 (审核ID: {audit_dict["id"]})',
                        'audit_status': 'pending',
                        'audit_task_id': audit_dict['id']
                    }
                else:
                    # 自动创建审核任务
                    self._create_audit_request(c, conn, task_id, task_dict)
                    self.stats['audit_requests_created'] += 1
                    self.stats['blocked_executions'] += 1
                    
                    return {
                        'allowed': False,
                        'action': 'create_audit',
                        'message': '任务已提交审核，请等待审核通过后执行',
                        'audit_status': 'pending'
                    }
            
            else:
                self.stats['blocked_executions'] += 1
                return {
                    'allowed': False,
                    'action': 'block',
                    'message': f'未知的审核状态: {audit_status}',
                    'audit_status': audit_status
                }
                
        finally:
            conn.close()
    
    def _create_audit_request(self, cursor, conn, task_id: int, task: Dict):
        """创建审核请求"""
        try:
            cursor.execute('''
                INSERT INTO manual_review_tasks 
                (task_type, title, description, source, source_id, status, priority, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
            ''', (
                'task_execution',
                f'审核任务: {task["title"]}',
                f'''任务ID: {task_id}
任务名称: {task["title"]}
优先级: {task.get("priority", "medium")}

该任务需要审核后才能执行。请评估:
1. 任务的必要性
2. 执行风险
3. 资源需求
4. 预期收益''',
                'supervisor_system',
                task_id,
                'pending',
                task.get('priority', 'medium')
            ))
            
            # 更新任务的审核状态
            cursor.execute('''
                UPDATE tasks 
                SET audit_status = 'pending', updated_at = datetime('now')
                WHERE id = ?
            ''', (task_id,))
            
            conn.commit()
            logger.info(f"✅ 已为任务 {task_id} 创建审核请求")
            
        except Exception as e:
            logger.error(f"创建审核请求失败: {e}")
            raise
    
    def scan_unaudited_tasks(self) -> List[Dict[str, Any]]:
        """扫描所有未审核的任务"""
        conn = self.get_db()
        c = conn.cursor()
        
        try:
            c.execute('''
                SELECT 
                    t.id,
                    t.title,
                    t.priority,
                    t.status,
                    t.audit_status,
                    t.created_at,
                    p.name as project_name
                FROM tasks t
                LEFT JOIN projects p ON t.project_id = p.id
                WHERE t.requires_audit = 1 
                  AND (t.audit_status IS NULL OR t.audit_status = 'pending')
                  AND t.status != 'deleted'
                ORDER BY 
                    CASE t.priority 
                        WHEN 'high' THEN 1 
                        WHEN 'medium' THEN 2 
                        ELSE 3 
                    END,
                    t.created_at DESC
            ''')
            
            tasks = [dict(row) for row in c.fetchall()]
            
            # 为每个任务检查是否有审核记录
            for task in tasks:
                c.execute('''
                    SELECT id, status, created_at 
                    FROM manual_review_tasks 
                    WHERE source_id = ? AND task_type = 'task_execution'
                    ORDER BY created_at DESC 
                    LIMIT 1
                ''', (task['id'],))
                
                audit = c.fetchone()
                task['has_audit_request'] = audit is not None
                if audit:
                    task['audit_request'] = dict(audit)
            
            return tasks
            
        finally:
            conn.close()
    
    def auto_create_audit_requests(self) -> Dict[str, Any]:
        """自动为未审核的任务创建审核请求"""
        unaudited = self.scan_unaudited_tasks()
        created = 0
        skipped = 0
        
        conn = self.get_db()
        c = conn.cursor()
        
        try:
            for task in unaudited:
                if not task['has_audit_request']:
                    self._create_audit_request(c, conn, task['id'], task)
                    created += 1
                else:
                    skipped += 1
            
            return {
                'success': True,
                'scanned': len(unaudited),
                'created': created,
                'skipped': skipped,
                'message': f'扫描了 {len(unaudited)} 个任务，创建了 {created} 个审核请求'
            }
            
        except Exception as e:
            logger.error(f"自动创建审核请求失败: {e}")
            return {
                'success': False,
                'error': str(e)
            }
            
        finally:
            conn.close()
    
    def generate_audit_report(self) -> AuditReport:
        """生成审核报告"""
        conn = self.get_db()
        c = conn.cursor()
        
        try:
            # 1. 总体统计
            c.execute('''
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN audit_status = 'pending' THEN 1 ELSE 0 END) as pending,
                    SUM(CASE WHEN audit_status = 'approved' THEN 1 ELSE 0 END) as approved,
                    SUM(CASE WHEN audit_status = 'rejected' THEN 1 ELSE 0 END) as rejected,
                    SUM(CASE WHEN audit_status = 'executing' THEN 1 ELSE 0 END) as executing,
                    SUM(CASE WHEN audit_status = 'completed' THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN audit_status = 'failed' THEN 1 ELSE 0 END) as failed
                FROM tasks
                WHERE requires_audit = 1 AND status != 'deleted'
            ''')
            
            stats = dict(c.fetchone())
            
            # 2. 计算平均审核时间
            c.execute('''
                SELECT 
                    AVG(
                        (julianday(m.completed_at) - julianday(m.created_at)) * 24
                    ) as avg_hours
                FROM manual_review_tasks m
                WHERE m.status IN ('approved', 'rejected')
                  AND m.completed_at IS NOT NULL
            ''')
            
            avg_time = c.fetchone()[0] or 0
            
            # 3. 获取关键任务（高优先级待审核）
            c.execute('''
                SELECT 
                    t.id,
                    t.title,
                    t.priority,
                    t.created_at,
                    m.id as audit_id,
                    m.created_at as audit_created_at
                FROM tasks t
                LEFT JOIN manual_review_tasks m ON t.id = m.source_id
                WHERE t.requires_audit = 1
                  AND t.audit_status = 'pending'
                  AND t.priority = 'high'
                ORDER BY t.created_at DESC
                LIMIT 10
            ''')
            
            critical_tasks = [dict(row) for row in c.fetchall()]
            
            # 4. 生成建议
            recommendations = []
            
            if stats.get('pending', 0) > 10:
                recommendations.append(f"有 {stats['pending']} 个任务待审核，建议加快审核进度")
            
            if avg_time > 24:
                recommendations.append(f"平均审核时间为 {avg_time:.1f} 小时，建议优化审核流程")
            
            if stats.get('rejected', 0) > stats.get('approved', 0):
                recommendations.append("拒绝率较高，建议检查任务生成质量")
            
            if not recommendations:
                recommendations.append("审核系统运行正常")
            
            return AuditReport(
                report_time=datetime.now().isoformat(),
                total_tasks=stats.get('total', 0),
                pending_audit=stats.get('pending', 0),
                approved=stats.get('approved', 0),
                rejected=stats.get('rejected', 0),
                executing=stats.get('executing', 0),
                completed=stats.get('completed', 0),
                failed=stats.get('failed', 0),
                avg_audit_time_hours=round(avg_time, 2),
                critical_tasks=critical_tasks,
                recommendations=recommendations
            )
            
        finally:
            conn.close()
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """获取执行统计"""
        return {
            'stats': self.stats.copy(),
            'timestamp': datetime.now().isoformat()
        }
    
    def reset_stats(self):
        """重置统计"""
        self.stats = {
            'tasks_checked': 0,
            'blocked_executions': 0,
            'audit_requests_created': 0
        }
    
    def notify_pending_audits(self) -> Dict[str, Any]:
        """提醒待审核任务"""
        pending = self.scan_unaudited_tasks()
        
        high_priority = [t for t in pending if t['priority'] == 'high']
        medium_priority = [t for t in pending if t['priority'] == 'medium']
        low_priority = [t for t in pending if t['priority'] == 'low']
        
        message = f"""
📋 **待审核任务提醒**

总计: {len(pending)} 个任务待审核

🔴 高优先级: {len(high_priority)} 个
🟡 中优先级: {len(medium_priority)} 个  
🟢 低优先级: {len(low_priority)} 个

请及时处理待审核任务，确保工作流程顺畅。
"""
        
        # 这里可以添加发送到飞书/邮件等的逻辑
        logger.info(message)
        
        return {
            'total': len(pending),
            'high': len(high_priority),
            'medium': len(medium_priority),
            'low': len(low_priority),
            'message': message
        }


# 全局监督系统实例
supervisor = SupervisorSystem()


def enforce_audit_before_execution(task_id: int) -> Dict[str, Any]:
    """
    执行前强制审核检查
    
    这是主要的对外接口，在任务执行前调用
    """
    return supervisor.enforce_audit_policy(task_id)


def get_audit_report() -> AuditReport:
    """获取审核报告"""
    return supervisor.generate_audit_report()


def scan_and_create_audits() -> Dict[str, Any]:
    """扫描并创建审核请求"""
    return supervisor.auto_create_audit_requests()


if __name__ == '__main__':
    print("=" * 60)
    print("增强型监督系统测试")
    print("=" * 60)
    
    # 1. 扫描未审核任务
    print("\n📊 扫描未审核任务...")
    unaudited = supervisor.scan_unaudited_tasks()
    print(f"发现 {len(unaudited)} 个未审核任务")
    
    for task in unaudited[:5]:
        print(f"  - [{task['priority']}] {task['title']}")
    
    # 2. 生成报告
    print("\n📈 生成审核报告...")
    report = supervisor.generate_audit_report()
    print(f"总计: {report.total_tasks}")
    print(f"待审核: {report.pending_audit}")
    print(f"已通过: {report.approved}")
    print(f"已拒绝: {report.rejected}")
    print(f"平均审核时间: {report.avg_audit_time_hours:.1f} 小时")
    
    # 3. 提醒
    print("\n🔔 待审核提醒...")
    reminder = supervisor.notify_pending_audits()
    print(reminder['message'])
