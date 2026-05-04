#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SDS任务生成频率限制器 (Task Generation Rate Limiter)
功能：每个目标(project_id)每24小时最多生成N个任务，防止任务泛滥

设计依据：
- 2026年主流Agent调度系统普遍采用频率限制机制
- 参考OpenAI Swarm框架的任务生成最佳实践
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
from lib.db_connector import execute_query


class TaskRateLimiter:
    """任务生成频率限制器"""
    
    # 默认配置
    DEFAULT_MAX_TASKS_PER_24H = 2
    DEFAULT_WINDOW_HOURS = 24
    
    def __init__(self, max_tasks: int = None, window_hours: int = None):
        """
        初始化频率限制器
        
        Args:
            max_tasks: 每窗口最大任务数（默认2）
            window_hours: 时间窗口小时数（默认24）
        """
        self.max_tasks = max_tasks if max_tasks is not None else self.DEFAULT_MAX_TASKS_PER_24H
        self.window_hours = window_hours if window_hours is not None else self.DEFAULT_WINDOW_HOURS
    
    def check_rate_limit(self, project_id: int) -> Tuple[bool, Dict]:
        """
        检查指定目标是否超出频率限制
        
        Args:
            project_id: 目标项目ID
        
        Returns:
            (是否允许生成, 详细信息字典)
            - allowed: True表示允许生成
            - current_count: 当前窗口内已生成数量
            - max_allowed: 最大允许数量
            - window_start: 窗口开始时间
            - next_available: 下一个可生成时间（如果已满）
        """
        now = datetime.now()
        window_start = now - timedelta(hours=self.window_hours)
        
        # 查询当前窗口内自动生成的任务数量
        sql = """
            SELECT COUNT(*) as cnt
            FROM tasks
            WHERE project_id = %s
              AND task_type LIKE 'auto_generated%%'
              AND created_at >= %s
        """
        result = execute_query(sql, (project_id, window_start))
        current_count = result[0].get('cnt', 0) if result and len(result) > 0 else 0
        
        allowed = current_count < self.max_tasks
        
        info = {
            'allowed': allowed,
            'project_id': project_id,
            'current_count': current_count,
            'max_allowed': self.max_tasks,
            'window_hours': self.window_hours,
            'window_start': window_start.strftime('%Y-%m-%d %H:%M:%S'),
            'remaining': max(0, self.max_tasks - current_count),
        }
        
        if not allowed:
            # 计算下一个可生成时间（最早的任务创建时间 + 窗口）
            earliest = execute_query("""
                SELECT MIN(created_at) as earliest
                FROM tasks
                WHERE project_id = %s
                  AND task_type LIKE 'auto_generated%%'
                  AND created_at >= %s
            """, (project_id, window_start))
            if earliest and earliest[0]['earliest']:
                next_avail = earliest[0]['earliest'] + timedelta(hours=self.window_hours)
                info['next_available'] = next_avail.strftime('%Y-%m-%d %H:%M:%S')
            else:
                info['next_available'] = now.strftime('%Y-%m-%d %H:%M:%S')
        
        return allowed, info
    
    def check_batch_rate_limit(self, project_ids: list) -> Dict[int, Tuple[bool, Dict]]:
        """
        批量检查多个目标的频率限制
        
        Args:
            project_ids: 项目ID列表
        
        Returns:
            {project_id: (allowed, info)} 字典
        """
        results = {}
        for pid in project_ids:
            results[pid] = self.check_rate_limit(pid)
        return results
    
    def get_all_targets_status(self) -> list:
        """
        获取所有目标的频率限制状态
        
        Returns:
            所有project_id的状态列表
        """
        # 获取所有有自动生成任务的项目
        sql = """
            SELECT DISTINCT project_id
            FROM tasks
            WHERE task_type LIKE 'auto_generated%%'
              AND project_id IS NOT NULL
            ORDER BY project_id
        """
        projects = execute_query(sql)
        
        results = []
        for p in projects:
            pid = p['project_id']
            allowed, info = self.check_rate_limit(pid)
            results.append(info)
        
        return results


def check_and_log(project_id: int, limiter: TaskRateLimiter = None) -> Tuple[bool, str]:
    """
    便捷函数：检查频率限制并返回日志消息
    
    Args:
        project_id: 项目ID
        limiter: 限制器实例（None使用默认配置）
    
    Returns:
        (是否允许, 日志消息)
    """
    if limiter is None:
        limiter = TaskRateLimiter()
    
    allowed, info = limiter.check_rate_limit(project_id)
    
    if allowed:
        log = (
            f"✅ [频率限制] project_id={project_id}: "
            f"允许生成 ({info['current_count']}/{info['max_allowed']})"
        )
    else:
        log = (
            f"⛔ [频率限制] project_id={project_id}: "
            f"已超出限制 ({info['current_count']}/{info['max_allowed']}), "
            f"下次可生成时间: {info.get('next_available', '未知')}"
        )
    
    return allowed, log


if __name__ == "__main__":
    print("=" * 60)
    print("SDS任务生成频率限制器 - 状态检查")
    print("=" * 60)
    
    limiter = TaskRateLimiter(max_tasks=2, window_hours=24)
    
    # 检查所有目标
    statuses = limiter.get_all_targets_status()
    
    for s in statuses:
        status_icon = "✅" if s['allowed'] else "⛔"
        print(f"{status_icon} project_id={s['project_id']}: "
              f"{s['current_count']}/{s['max_allowed']} "
              f"(窗口: {s['window_hours']}h)")
        if not s['allowed']:
            print(f"   下次可生成: {s['next_available']}")
    
    if not statuses:
        print("暂无自动生成任务记录")
