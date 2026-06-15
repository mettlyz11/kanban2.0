#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
任务生成守卫模块 - SDS v4.3
功能：
1. 每目标每24小时最多生成2个任务的硬限制
2. 标题前缀15字精确匹配去重机制
3. Pending任务水位控制（每目标最多3个pending）
4. 任务生成日志与审计追踪

创建日期: 2026-04-27
任务: #2110 - 调度系统频率限制与去重机制升级
"""

import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'scripts'))
from lib.db_connector import get_db_connection, execute_query, execute_update


class RejectReason(Enum):
    """拒绝原因枚举"""
    FREQUENCY_LIMIT = "frequency_limit"          # 频率超限
    DUPLICATE_TITLE = "duplicate_title"          # 标题重复
    PENDING_WATERMARK = "pending_watermark"      # Pending水位超限
    SUCCESS = "success"                          # 通过


@dataclass
class GenerationResult:
    """任务生成结果"""
    allowed: bool
    reason: RejectReason
    message: str
    details: Dict[str, Any]


class TaskGenerationGuardV43:
    """
    任务生成守卫 v4.3
    
    实现四层防护:
    1. 频率限制: 每目标每24小时最多2个任务
    2. 标题去重: 15字前缀精确匹配
    3. 水位控制: 每目标最多3个pending任务
    4. 审计追踪: 完整日志记录
    """
    
    def __init__(self, 
                 max_tasks_per_24h: int = 2,
                 max_pending_per_goal: int = 3,
                 duplicate_prefix_length: int = 15,
                 window_hours: int = 24):
        """
        初始化守卫
        
        Args:
            max_tasks_per_24h: 每24小时每目标最大任务数
            max_pending_per_goal: 每目标最大pending数
            duplicate_prefix_length: 去重前缀长度
            window_hours: 频率统计窗口（小时）
        """
        self.max_tasks_per_24h = max_tasks_per_24h
        self.max_pending_per_goal = max_pending_per_goal
        self.duplicate_prefix_length = duplicate_prefix_length
        self.window_hours = window_hours
        
        self._init_tables()
    
    def _init_tables(self):
        """初始化所需的数据表 - 使用兼容现有表结构"""
        # 1. 任务生成频率表（已存在，使用target_id代替goal_id）
        # 表已存在，不需要创建
        pass
    
    def can_generate_task(self, goal_id: int, task_title: str) -> GenerationResult:
        """
        检查是否可以生成新任务（主入口）
        
        Args:
            goal_id: 目标ID
            task_title: 任务标题
            
        Returns:
            GenerationResult: 检查结果
        """
        details = {}
        
        # 检查1: Pending任务水位控制
        pending_result = self._check_pending_watermark(goal_id)
        details['pending'] = pending_result
        if not pending_result['allowed']:
            return GenerationResult(
                allowed=False,
                reason=RejectReason.PENDING_WATERMARK,
                message=f"Pending任务水位超限: 当前{pending_result['count']}个, 限制{self.max_pending_per_goal}个",
                details=details
            )
        
        # 检查2: 频率限制
        frequency_result = self._check_frequency_limit(goal_id)
        details['frequency'] = frequency_result
        if not frequency_result['allowed']:
            return GenerationResult(
                allowed=False,
                reason=RejectReason.FREQUENCY_LIMIT,
                message=f"生成频率超限: 24小时内已生成{frequency_result['count']}个, 限制{self.max_tasks_per_24h}个",
                details=details
            )
        
        # 检查3: 标题去重
        duplicate_result = self._check_duplicate_title(goal_id, task_title)
        details['duplicate'] = duplicate_result
        if not duplicate_result['allowed']:
            return GenerationResult(
                allowed=False,
                reason=RejectReason.DUPLICATE_TITLE,
                message=f"标题重复: 前缀\"{duplicate_result['prefix']}\"已存在任务ID {duplicate_result['duplicate_id']}",
                details=details
            )
        
        # 所有检查通过
        return GenerationResult(
            allowed=True,
            reason=RejectReason.SUCCESS,
            message="所有检查通过，可以生成任务",
            details=details
        )
    
    def _check_frequency_limit(self, goal_id: int) -> Dict[str, Any]:
        """检查频率限制"""
        cutoff_time = datetime.now() - timedelta(hours=self.window_hours)
        
        sql = """
            SELECT COUNT(*) as count
            FROM task_generation_frequency
            WHERE target_type = 'goal' AND target_id = %s AND generated_at >= %s
        """
        
        result = execute_query(sql, (goal_id, cutoff_time))
        count = result[0]['count'] if result else 0
        
        return {
            'allowed': count < self.max_tasks_per_24h,
            'count': count,
            'limit': self.max_tasks_per_24h,
            'window_hours': self.window_hours
        }
    
    def _check_pending_watermark(self, goal_id: int) -> Dict[str, Any]:
        """检查pending任务水位"""
        sql = """
            SELECT COUNT(*) as count
            FROM tasks
            WHERE goal_id = %s AND status IN ('pending', 'ready', 'queued')
        """
        
        result = execute_query(sql, (goal_id,))
        count = result[0]['count'] if result else 0
        
        return {
            'allowed': count < self.max_pending_per_goal,
            'count': count,
            'limit': self.max_pending_per_goal
        }
    
    def _check_duplicate_title(self, goal_id: int, task_title: str) -> Dict[str, Any]:
        """检查标题重复（15字前缀精确匹配）"""
        title_prefix = task_title[:self.duplicate_prefix_length]
        
        cutoff_time = datetime.now() - timedelta(hours=self.window_hours)
        
        # 检查同一目标下，时间窗口内的标题前缀重复
        sql = """
            SELECT id, title, created_at
            FROM tasks
            WHERE goal_id = %s
              AND LEFT(title, %s) = %s
              AND created_at >= %s
              AND status NOT IN ('cancelled', 'deleted')
            ORDER BY created_at DESC
            LIMIT 1
        """
        
        result = execute_query(sql, (goal_id, self.duplicate_prefix_length, title_prefix, cutoff_time))
        
        if result:
            duplicate_task = result[0]
            return {
                'allowed': False,
                'prefix': title_prefix,
                'duplicate_id': duplicate_task['id'],
                'duplicate_title': duplicate_task['title'],
                'duplicate_time': duplicate_task['created_at']
            }
        
        return {
            'allowed': True,
            'prefix': title_prefix
        }
    
    def record_task_generation(self, goal_id: int, task_id: int, task_title: str) -> bool:
        """
        记录任务生成事件（成功生成后调用）
        
        Args:
            goal_id: 目标ID
            task_id: 生成的任务ID
            task_title: 任务标题
            
        Returns:
            bool: 是否成功记录
        """
        try:
            # 记录频率统计（使用现有表结构）
            sql1 = """
                INSERT INTO task_generation_frequency
                (target_type, target_id, task_id, task_title, generated_at)
                VALUES ('goal', %s, %s, %s, %s)
            """
            execute_update(sql1, (goal_id, task_id, task_title[:500], datetime.now()))
            
            # 记录审计日志（允许）- 使用简化版兼容现有表结构
            self._write_audit_log_simple(
                goal_id=goal_id,
                task_title=task_title,
                task_id=task_id,
                accepted=True,
                reject_reason=None
            )
            
            return True
        except Exception as e:
            # print(f"[ERROR] 记录任务生成失败: {e}")
            return False
    
    def record_task_rejection(self, goal_id: int, task_title: str, 
                              reason: RejectReason, details: Dict[str, Any]) -> bool:
        """
        记录任务被拒绝事件（生成失败时调用）
        
        Args:
            goal_id: 目标ID
            task_title: 任务标题
            reason: 拒绝原因
            details: 详细信息
            
        Returns:
            bool: 是否成功记录
        """
        try:
            self._write_audit_log_simple(
                goal_id=goal_id,
                task_title=task_title,
                task_id=0,
                accepted=False,
                reject_reason=reason.value
            )
            return True
        except Exception as e:
            # print(f"[ERROR] 记录任务拒绝失败: {e}")
            return False
    
    def _write_audit_log_simple(self, goal_id: int, task_title: str, task_id: int,
                                 accepted: bool, reject_reason: Optional[str]):
        """写入审计日志 - 兼容现有表结构"""
        title_prefix = task_title[:15]
        
        sql = """
            INSERT INTO task_generation_audit
            (title, title_prefix, project_id, target_id, accepted, reject_reasons, task_id, logged_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        execute_update(sql, (
            task_title[:500],
            title_prefix,
            0,  # project_id 设为0（无项目关联）
            goal_id,  # target_id 存储 goal_id
            1 if accepted else 0,
            reject_reason or '',
            task_id or 0,
            datetime.now()
        ))
    
    def _get_frequency_count(self, goal_id: int) -> int:
        """获取当前频率计数"""
        result = self._check_frequency_limit(goal_id)
        return result['count']
    
    def _get_pending_count(self, goal_id: int) -> int:
        """获取当前pending计数"""
        result = self._check_pending_watermark(goal_id)
        return result['count']
    
    def get_goal_status(self, goal_id: int) -> Dict[str, Any]:
        """
        获取目标的完整状态
        
        Args:
            goal_id: 目标ID
            
        Returns:
            包含频率、pending、配额等信息的字典
        """
        frequency = self._check_frequency_limit(goal_id)
        pending = self._check_pending_watermark(goal_id)
        
        # 计算配额何时释放
        cutoff_time = datetime.now() - timedelta(hours=self.window_hours)
        sql = """
            SELECT MIN(generated_at) as earliest_time
            FROM task_generation_frequency
            WHERE target_type = 'goal' AND target_id = %s AND generated_at >= %s
        """
        result = execute_query(sql, (goal_id, cutoff_time))
        
        quota_release_time = None
        if result and result[0]['earliest_time'] and not frequency['allowed']:
            quota_release_time = result[0]['earliest_time'] + timedelta(hours=self.window_hours)
        
        return {
            'goal_id': goal_id,
            'frequency': {
                'used': frequency['count'],
                'limit': frequency['limit'],
                'remaining': frequency['limit'] - frequency['count'],
                'allowed': frequency['allowed'],
                'quota_release_time': quota_release_time
            },
            'pending_tasks': {
                'count': pending['count'],
                'limit': pending['limit'],
                'available_slots': pending['limit'] - pending['count'],
                'allowed': pending['allowed']
            }
        }
    
    def get_statistics(self, hours: int = 24) -> Dict[str, Any]:
        """
        获取统计数据
        
        Args:
            hours: 统计时间范围（小时）
            
        Returns:
            统计信息字典
        """
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        # 总生成数
        sql1 = "SELECT COUNT(*) as count FROM task_generation_frequency WHERE generated_at >= %s"
        result1 = execute_query(sql1, (cutoff_time,))
        generated = result1[0]['count'] if result1 else 0
        
        # 总拒绝数（兼容现有表结构: accepted=0 表示拒绝）
        sql2 = "SELECT COUNT(*) as count FROM task_generation_audit WHERE accepted = 0 AND logged_at >= %s"
        result2 = execute_query(sql2, (cutoff_time,))
        rejected = result2[0]['count'] if result2 else 0
        
        # 按原因统计拒绝
        sql3 = """
            SELECT reject_reasons as reject_reason, COUNT(*) as count
            FROM task_generation_audit
            WHERE accepted = 0 AND logged_at >= %s
            GROUP BY reject_reasons
        """
        reject_by_reason = execute_query(sql3, (cutoff_time,))
        
        # 按目标统计
        sql4 = """
            SELECT target_id as goal_id, COUNT(*) as count
            FROM task_generation_frequency
            WHERE generated_at >= %s AND target_type = 'goal'
            GROUP BY target_id
            ORDER BY count DESC
            LIMIT 5
        """
        top_goals = execute_query(sql4, (cutoff_time,))
        
        return {
            'period_hours': hours,
            'tasks_generated': generated,
            'tasks_rejected': rejected,
            'rejection_rate': rejected / (generated + rejected) if (generated + rejected) > 0 else 0,
            'reject_by_reason': {r['reject_reason']: r['count'] for r in reject_by_reason},
            'top_active_goals': top_goals
        }
    
    def clear_expired_data(self, older_than_days: int = 30) -> int:
        """
        清理过期数据
        
        Args:
            older_than_days: 保留天数
            
        Returns:
            清理的记录数
        """
        cutoff = datetime.now() - timedelta(days=older_than_days)
        
        sql1 = "DELETE FROM task_generation_frequency WHERE generated_at < %s"
        sql2 = "DELETE FROM task_generation_audit WHERE logged_at < %s"
        
        count1 = execute_update(sql1, (cutoff,))
        count2 = execute_update(sql2, (cutoff,))
        
        return count1 + count2


# 便捷函数
def can_generate_task_v43(goal_id: int, task_title: str) -> GenerationResult:
    """V4.3便捷函数: 检查是否可以生成任务"""
    guard = TaskGenerationGuardV43()
    return guard.can_generate_task(goal_id, task_title)


def record_task_generation_v43(goal_id: int, task_id: int, task_title: str) -> bool:
    """V4.3便捷函数: 记录任务生成"""
    guard = TaskGenerationGuardV43()
    return guard.record_task_generation(goal_id, task_id, task_title)


if __name__ == '__main__':
    # print("=" * 60)
    # print("  SDS v4.3 任务生成守卫模块")
    # print("=" * 60)
    
    guard = TaskGenerationGuardV43()
    
    # 显示配置
    # print(f"\n配置参数:")
    # print(f"  - 每24小时每目标最大任务数: {guard.max_tasks_per_24h}")
    # print(f"  - 每目标最大Pending任务数: {guard.max_pending_per_goal}")
    # print(f"  - 去重标题前缀长度: {guard.duplicate_prefix_length}字")
    
    # 显示统计
    stats = guard.get_statistics(hours=24)
    # print(f"\n过去24小时统计:")
    # print(f"  - 已生成任务: {stats['tasks_generated']}")
    # print(f"  - 已拒绝任务: {stats['tasks_rejected']}")
    # print(f"  - 拒绝率: {stats['rejection_rate']:.1%}")
    
    if stats['reject_by_reason']:
        # print(f"\n拒绝原因分布:")
        for reason, count in stats['reject_by_reason'].items():
            # print(f"  - {reason}: {count}")
    
    # print("\n✅ V4.3 守卫模块加载成功")
