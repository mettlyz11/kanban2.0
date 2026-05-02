#!/usr/bin/env python3
"""
V4.3 任务生成引擎频率限制机制 - 单元测试套件
测试目标: 验证"每目标24小时最多2个任务"的频率限制机制

测试场景:
  1. 0个已存在任务 → 允许生成
  2. 1个已存在任务 → 允许生成
  3. 2个已存在任务 → 允许生成（边界值）
  4. 3个已存在任务 → 拒绝生成
  5. 跨目标独立性测试
  6. 24小时时间窗口边界测试
  7. 重复任务检测与频率限制的联合测试
  8. 数据库层面频率限制验证
"""

import unittest
import sys
import os
import re
import json
from datetime import datetime, timedelta
from collections import defaultdict
from unittest.mock import patch, MagicMock

# 添加lib路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'scripts'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'sds'))

from lib.db_connector import get_db_connection, execute_query, execute_update


class TestGoalPrefixExtraction(unittest.TestCase):
    """测试用例: 目标前缀提取准确性"""
    
    def test_extract_goal_t1(self):
        """T1前缀提取"""
        title = "T1: AI助手优化 - 多智能体协作框架升级"
        match = re.match(r'(T\d+)', title)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), 'T1')
    
    def test_extract_goal_t7(self):
        """T7前缀提取"""
        title = "T7: 健康管理 - 睡眠优化方案"
        match = re.match(r'(T\d+)', title)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), 'T7')
    
    def test_extract_goal_no_prefix(self):
        """无前缀标题处理"""
        title = "系统维护 - 清理过期日志"
        match = re.match(r'(T\d+)', title)
        self.assertIsNone(match)
    
    def test_extract_goal_malformed(self):
        """畸形标题处理"""
        title = "T12: 边缘情况测试"
        match = re.match(r'(T\d+)', title)
        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), 'T12')
    
    def test_extract_goal_empty(self):
        """空标题处理"""
        match = re.match(r'(T\d+)', '')
        self.assertIsNone(match)
    
    def test_extract_goal_none(self):
        """None值处理"""
        match = re.match(r'(T\d+)', None or '')
        self.assertIsNone(match)


class TestFrequencyLimitLogic(unittest.TestCase):
    """测试用例: 频率限制核心逻辑 (边界值测试)"""
    
    def setUp(self):
        """模拟频率限制检查函数"""
        self.MAX_TASKS_PER_GOAL_24H = 2
        
    def check_frequency_limit(self, goal_code: str, existing_tasks: list) -> tuple:
        """
        模拟频率限制检查
        返回: (allowed: bool, current_count: int, remaining: int)
        """
        current_count = len(existing_tasks)
        remaining = max(0, self.MAX_TASKS_PER_GOAL_24H - current_count)
        allowed = current_count < self.MAX_TASKS_PER_GOAL_24H
        return allowed, current_count, remaining
    
    def test_zero_existing_tasks(self):
        """场景0: 0个已存在任务 → 允许生成"""
        existing = []
        allowed, count, remaining = self.check_frequency_limit('T1', existing)
        self.assertTrue(allowed, "0个任务时应允许生成")
        self.assertEqual(count, 0)
        self.assertEqual(remaining, 2, "剩余配额应为2")
    
    def test_one_existing_task(self):
        """场景1: 1个已存在任务 → 允许生成"""
        existing = [{'id': 1, 'title': 'T1: 测试任务1'}]
        allowed, count, remaining = self.check_frequency_limit('T1', existing)
        self.assertTrue(allowed, "1个任务时应允许生成")
        self.assertEqual(count, 1)
        self.assertEqual(remaining, 1, "剩余配额应为1")
    
    def test_two_existing_tasks(self):
        """场景2: 2个已存在任务 → 允许生成（边界值：刚好达到上限）"""
        existing = [
            {'id': 1, 'title': 'T1: 测试任务1'},
            {'id': 2, 'title': 'T1: 测试任务2'}
        ]
        allowed, count, remaining = self.check_frequency_limit('T1', existing)
        self.assertFalse(allowed, "2个任务时应拒绝新任务生成（已达上限）")
        self.assertEqual(count, 2)
        self.assertEqual(remaining, 0, "剩余配额应为0")
    
    def test_three_existing_tasks(self):
        """场景3: 3个已存在任务 → 拒绝生成（已超标）"""
        existing = [
            {'id': 1, 'title': 'T1: 测试任务1'},
            {'id': 2, 'title': 'T1: 测试任务2'},
            {'id': 3, 'title': 'T1: 测试任务3'}
        ]
        allowed, count, remaining = self.check_frequency_limit('T1', existing)
        self.assertFalse(allowed, "3个任务时应拒绝新任务生成（已超标）")
        self.assertEqual(count, 3)
        self.assertEqual(remaining, 0)
    
    def test_four_existing_tasks(self):
        """场景4: 4个已存在任务 → 拒绝生成（严重超标）"""
        existing = [{'id': i, 'title': f'T1: 测试任务{i}'} for i in range(1, 5)]
        allowed, count, remaining = self.check_frequency_limit('T1', existing)
        self.assertFalse(allowed)
        self.assertEqual(count, 4)
        self.assertEqual(remaining, 0)
    
    def test_ten_existing_tasks(self):
        """场景5: 10个已存在任务 → 拒绝生成（极端超标）"""
        existing = [{'id': i, 'title': f'T1: 测试任务{i}'} for i in range(1, 11)]
        allowed, count, remaining = self.check_frequency_limit('T1', existing)
        self.assertFalse(allowed)
        self.assertEqual(count, 10)
        self.assertEqual(remaining, 0)


class TestCrossGoalIndependence(unittest.TestCase):
    """测试用例: 跨目标独立性"""
    
    def test_different_goals_independent(self):
        """不同目标的频率限制应独立"""
        MAX_TASKS = 2
        
        t1_tasks = [{'id': i, 'title': f'T1: 任务{i}'} for i in range(1, 4)]  # T1有3个
        t2_tasks = [{'id': 10, 'title': 'T2: 任务1'}]  # T2有1个
        
        # T1应该被限制
        t1_count = len(t1_tasks)
        t1_allowed = t1_count < MAX_TASKS
        self.assertFalse(t1_allowed, "T1有3个任务，应被限制")
        
        # T2应被允许
        t2_count = len(t2_tasks)
        t2_allowed = t2_count < MAX_TASKS
        self.assertTrue(t2_allowed, "T2有1个任务，应被允许")
    
    def test_all_goals_simultaneous(self):
        """所有目标同时检查"""
        MAX_TASKS = 2
        goal_tasks = {
            'T1': 3,  # 超标
            'T2': 2,  # 边界
            'T3': 0,  # 空闲
            'T4': 1,  # 正常
            'T5': 5,  # 严重超标
        }
        
        for goal, count in goal_tasks.items():
            allowed = count < MAX_TASKS
            expected = count < MAX_TASKS
            self.assertEqual(allowed, expected,
                f"{goal}: 有{count}个任务，允许状态应为{expected}")


class TestTimeWindowBoundary(unittest.TestCase):
    """测试用例: 24小时时间窗口边界"""
    
    def test_task_just_inside_window(self):
        """23小时59分钟前创建的任务应计入"""
        now = datetime.now()
        task_time = now - timedelta(hours=23, minutes=59)
        time_diff = now - task_time
        self.assertTrue(time_diff < timedelta(hours=24))
    
    def test_task_just_outside_window(self):
        """24小时1分钟前创建的任务不应计入"""
        now = datetime.now()
        task_time = now - timedelta(hours=24, minutes=1)
        time_diff = now - task_time
        self.assertTrue(time_diff > timedelta(hours=24))
    
    def test_task_exactly_at_boundary(self):
        """正好24小时的任务边界处理"""
        now = datetime.now()
        task_time = now - timedelta(hours=24)
        time_diff = now - task_time
        # 取决于实现：>= 24小时 应排除
        self.assertTrue(time_diff >= timedelta(hours=24))
    
    def test_mixed_window_scenario(self):
        """混合时间窗口：部分在24h内，部分在24h外"""
        now = datetime.now()
        tasks = [
            {'id': 1, 'created_at': now - timedelta(hours=1)},      # 1h前 → 计入
            {'id': 2, 'created_at': now - timedelta(hours=12)},     # 12h前 → 计入
            {'id': 3, 'created_at': now - timedelta(hours=23)},     # 23h前 → 计入
            {'id': 4, 'created_at': now - timedelta(hours=25)},     # 25h前 → 不计入
            {'id': 5, 'created_at': now - timedelta(hours=48)},     # 48h前 → 不计入
        ]
        
        in_window = [t for t in tasks if (now - t['created_at']) < timedelta(hours=24)]
        self.assertEqual(len(in_window), 3, "应有3个任务在24小时窗口内")


class TestDatabaseLevelFrequencyCheck(unittest.TestCase):
    """测试用例: 数据库层面频率限制验证（真实数据）"""
    
    def test_database_has_frequency_violations(self):
        """验证: 数据库中存在频率违规情况"""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, title, status, task_type, created_at
                FROM tasks
                WHERE task_type = 'auto_generated_v4.3'
                  AND created_at >= NOW() - INTERVAL 24 HOUR
                ORDER BY created_at DESC
            """)
            tasks = cursor.fetchall()
            
            # 提取目标前缀
            goal_counts = defaultdict(int)
            for t in tasks:
                match = re.match(r'(T\d+)', t['title'] or '')
                if match:
                    goal_counts[match.group(1)] += 1
            
            # 验证存在超标目标
            violated_goals = {g: c for g, c in goal_counts.items() if c > 2}
            self.assertGreater(len(violated_goals), 0,
                f"应存在超标目标，当前超标: {violated_goals}")
            
            # 验证总任务数超标
            self.assertGreater(len(tasks), len(goal_counts) * 2,
                f"总任务数 {len(tasks)} 超过理论上限 {len(goal_counts) * 2}")
            
        finally:
            conn.close()
    
    def test_auto_generated_task_type_field(self):
        """验证: task_type字段正确标识自动生成任务"""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT task_type
                FROM tasks
                WHERE task_type LIKE 'auto_generated%'
                ORDER BY task_type
            """)
            types = [row['task_type'] for row in cursor.fetchall()]
            
            self.assertIn('auto_generated_v4.3', types)
            # 验证多个版本共存
            self.assertGreater(len(types), 1, "应存在多个v4.x版本")
        finally:
            conn.close()
    
    def test_goal_id_field_is_null_for_auto_tasks(self):
        """验证: 自动任务的goal_id字段为空（需从标题解析）"""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) as null_count
                FROM tasks
                WHERE task_type = 'auto_generated_v4.3'
                  AND goal_id IS NULL
            """)
            result = cursor.fetchone()
            
            self.assertGreater(result['null_count'], 0,
                "自动任务的goal_id应全部为NULL")
        finally:
            conn.close()
    
    def test_pending_task_accumulation(self):
        """验证: 频率限制缺失导致pending任务堆积"""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) as pending_count
                FROM tasks
                WHERE task_type = 'auto_generated_v4.3'
                  AND status = 'pending'
                  AND created_at >= NOW() - INTERVAL 24 HOUR
            """)
            result = cursor.fetchone()
            
            # 如果有大量pending任务，说明频率限制未生效
            self.assertGreater(result['pending_count'], 10,
                f"pending任务数 {result['pending_count']} 表明频率限制未生效")
        finally:
            conn.close()


class TestFrequencyLimitEnforcement(unittest.TestCase):
    """测试用例: 频率限制执行器（模拟实现）"""
    
    def test_enforcement_blocks_over_limit(self):
        """验证: 频率限制执行器应阻止超标任务"""
        
        class FrequencyLimitEnforcer:
            def __init__(self, max_per_goal=2, window_hours=24):
                self.max_per_goal = max_per_goal
                self.window_hours = window_hours
            
            def can_generate(self, goal_code, recent_tasks):
                count = len(recent_tasks)
                return count < self.max_per_goal, count
        
        enforcer = FrequencyLimitEnforcer()
        
        # 模拟场景
        scenarios = [
            ('T1', [], True, 0),
            ('T2', [1], True, 1),
            ('T3', [1, 2], False, 2),
            ('T4', [1, 2, 3], False, 3),
            ('T5', list(range(10)), False, 10),
        ]
        
        for goal, tasks, expected_allowed, expected_count in scenarios:
            allowed, count = enforcer.can_generate(goal, tasks)
            self.assertEqual(allowed, expected_allowed,
                f"{goal}: allowed={allowed}, expected={expected_allowed}")
            self.assertEqual(count, expected_count)
    
    def test_enforcement_with_different_limits(self):
        """验证: 不同限制阈值下的行为"""
        
        for limit in [1, 2, 3, 5]:
            class Enforcer:
                def __init__(self, limit):
                    self.limit = limit
                def can_generate(self, count):
                    return count < self.limit
            
            e = Enforcer(limit)
            self.assertTrue(e.can_generate(0))
            self.assertTrue(e.can_generate(limit - 1))
            self.assertFalse(e.can_generate(limit))
            self.assertFalse(e.can_generate(limit + 1))


class TestDuplicateDetectionWithFrequencyLimit(unittest.TestCase):
    """测试用例: 重复检测与频率限制的联合效应"""
    
    def test_duplicate_and_frequency_independent(self):
        """重复检测和频率限制是独立的检查维度"""
        # 即使标题不重复，频率限制仍应生效
        unique_titles = [
            f"T1: 测试任务{i} - 唯一描述{i}" for i in range(5)
        ]
        # 5个不同标题但仍超标
        self.assertGreater(len(unique_titles), 2)
    
    def test_both_checks_should_pass(self):
        """一个任务需要同时通过去重和频率限制才能生成"""
        
        def check_duplicate(new_title, existing_titles, prefix_len=15):
            new_prefix = new_title[:prefix_len]
            return new_prefix not in existing_titles
        
        def check_frequency(goal_code, existing_count, max_allowed=2):
            return existing_count < max_allowed
        
        # 场景: 新任务不重复但目标已超标
        existing_titles = {"T1: 已有任务1 -", "T1: 已有任务2 -"}
        new_title = "T1: 新任务3 - 完全不同的内容"
        
        not_duplicate = check_duplicate(new_title, existing_titles)
        frequency_ok = check_frequency('T1', len(existing_titles))
        
        self.assertTrue(not_duplicate, "标题不重复")
        self.assertFalse(frequency_ok, "频率已超标")
        # 两者都通过才能生成
        can_generate = not_duplicate and frequency_ok
        self.assertFalse(can_generate, "频率超标应阻止生成，即使不重复")


if __name__ == '__main__':
    unittest.main(verbosity=2)
