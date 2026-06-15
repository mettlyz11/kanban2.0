#!/usr/bin/env python3
"""
任务频率限制模块 - SDS调度系统优化
功能: 限制每目标每24小时最多生成2个任务
实现: 基于滑动窗口计数器 + 数据库持久化
"""

import os
import sys
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'scripts'))
from lib.db_connector import get_db_connection, execute_query, execute_update


class TaskFrequencyLimiter:
    """任务频率限制器
    
    实现策略:
    1. 每目标每24小时最多生成2个任务
    2. 使用滑动窗口计数
    3. 支持多种目标类型: project, category, target_id
    4. 数据库持久化，重启不丢失
    """
    
    def __init__(self, max_tasks: int = 2, window_hours: int = 24):
        self.max_tasks = max_tasks
        self.window_hours = window_hours
        self._init_table()
    
    def _init_table(self):
        """初始化频率统计表"""
        sql = """
            CREATE TABLE IF NOT EXISTS task_generation_frequency (
                id INT AUTO_INCREMENT PRIMARY KEY,
                target_type VARCHAR(50) NOT NULL DEFAULT 'project',
                target_id INT NOT NULL,
                generated_at DATETIME NOT NULL,
                task_title VARCHAR(500),
                task_id INT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_target_time (target_type, target_id, generated_at),
                INDEX idx_task_id (task_id)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
        try:
            execute_update(sql, ())
        except Exception as e:
            # print(f"[WARN] 表创建可能已存在: {e}")
    
    def get_recent_task_count(self, target_id: int, target_type: str = 'project') -> int:
        """获取指定时间窗口内已生成的任务数量"""
        cutoff_time = datetime.now() - timedelta(hours=self.window_hours)
        
        sql = """
            SELECT COUNT(*) as count
            FROM task_generation_frequency
            WHERE target_type = %s
              AND target_id = %s
              AND generated_at >= %s
        """
        
        result = execute_query(sql, (target_type, target_id, cutoff_time))
        return result[0]['count'] if result else 0
    
    def can_generate_task(self, target_id: int, target_type: str = 'project') -> bool:
        """判断是否可以生成新任务"""
        count = self.get_recent_task_count(target_id, target_type)
        return count < self.max_tasks
    
    def record_task_generation(self, target_id: int, task_id: int, 
                                task_title: str, target_type: str = 'project') -> bool:
        """记录任务生成事件"""
        sql = """
            INSERT INTO task_generation_frequency 
            (target_type, target_id, generated_at, task_title, task_id)
            VALUES (%s, %s, %s, %s, %s)
        """
        
        try:
            execute_update(sql, (
                target_type, 
                target_id, 
                datetime.now(), 
                task_title[:500], 
                task_id
            ))
            return True
        except Exception as e:
            # print(f"[ERROR] 记录任务生成失败: {e}")
            return False
    
    def get_remaining_quota(self, target_id: int, target_type: str = 'project') -> Dict[str, Any]:
        """获取剩余配额信息"""
        count = self.get_recent_task_count(target_id, target_type)
        remaining = self.max_tasks - count
        
        # 计算最早的任务何时过期
        cutoff_time = datetime.now() - timedelta(hours=self.window_hours)
        sql = """
            SELECT MIN(generated_at) as earliest_time
            FROM task_generation_frequency
            WHERE target_type = %s
              AND target_id = %s
              AND generated_at >= %s
        """
        result = execute_query(sql, (target_type, target_id, cutoff_time))
        
        next_available = None
        if result and result[0]['earliest_time'] and remaining <= 0:
            earliest = result[0]['earliest_time']
            next_available = earliest + timedelta(hours=self.window_hours)
        
        return {
            'used': count,
            'remaining': max(0, remaining),
            'max_tasks': self.max_tasks,
            'window_hours': self.window_hours,
            'can_generate': remaining > 0,
            'next_available': next_available
        }
    
    def clear_expired_records(self, older_than_days: int = 7) -> int:
        """清理过期记录"""
        cutoff = datetime.now() - timedelta(days=older_than_days)
        sql = "DELETE FROM task_generation_frequency WHERE generated_at < %s"
        return execute_update(sql, (cutoff,))


# 便捷函数
def check_and_record_task(target_id: int, task_id: int, task_title: str,
                          target_type: str = 'project') -> Dict[str, Any]:
    """便捷函数: 检查配额并记录任务生成
    
    Returns:
        包含success和quota_info的字典
    """
    limiter = TaskFrequencyLimiter()
    quota = limiter.get_remaining_quota(target_id, target_type)
    
    if not quota['can_generate']:
        return {
            'success': False,
            'reason': '频率超限',
            'quota_info': quota
        }
    
    recorded = limiter.record_task_generation(target_id, task_id, task_title, target_type)
    
    return {
        'success': recorded,
        'quota_info': limiter.get_remaining_quota(target_id, target_type)
    }


if __name__ == '__main__':
    # 简单测试
    limiter = TaskFrequencyLimiter()
    # print("频率限制模块加载成功")
    # print(f"默认配置: 每目标每{limiter.window_hours}小时最多{limiter.max_tasks}个任务")
    
    # 测试一个示例项目
    test_project_id = 1
    quota = limiter.get_remaining_quota(test_project_id)
    # print(f"\n项目 #{test_project_id} 配额状态:")
    # print(f"  已使用: {quota['used']} / {quota['max_tasks']}")
    # print(f"  剩余: {quota['remaining']}")
    # print(f"  可生成: {quota['can_generate']}")
    if quota['next_available']:
        # print(f"  下次可用时间: {quota['next_available']}")
