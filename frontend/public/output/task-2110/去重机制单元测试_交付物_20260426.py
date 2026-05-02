#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
任务 #2110 交付物：去重机制单元测试 V4.3
测试频率限制、去重机制、水位控制
"""

import sys
import os
import unittest
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "sds" / "core"))

from rate_limit_v43 import RateLimitLayerV43
from dedup_v43 import TitlePrefixDedupV43, DedupResult


class TestRateLimitV43(unittest.TestCase):
    """频率限制 V4.3 测试"""
    
    def setUp(self):
        self.rate_limiter = RateLimitLayerV43(
            max_tasks_per_24h=2,
            max_pending_per_goal=3
        )
    
    def test_default_config(self):
        """测试默认配置"""
        self.assertEqual(self.rate_limiter.max_tasks_per_24h, 2)
        self.assertEqual(self.rate_limiter.max_pending_per_goal, 3)
    
    def test_rate_limit_decision_when_under_limit(self):
        """测试未达上限时的决策"""
        check_result = {
            'can_generate': True,
            'current_count': 1,
            'max_allowed': 2,
            'remaining_slots': 1
        }
        decision = self.rate_limiter._make_decision(check_result, True)
        self.assertTrue(decision.can_generate)
        self.assertEqual(decision.decision, 'allowed')
    
    def test_rate_limit_decision_when_over_limit(self):
        """测试超限时的决策"""
        check_result = {
            'can_generate': False,
            'current_count': 3,
            'max_allowed': 2,
            'remaining_slots': 0
        }
        decision = self.rate_limiter._make_decision(check_result, True)
        self.assertFalse(decision.can_generate)
        self.assertEqual(decision.decision, 'blocked_rate_limit')
    
    def test_pending_decision_when_under_limit(self):
        """测试pending水位未达上限"""
        check_result = {
            'can_generate': True,
            'current_pending': 2,
            'max_allowed': 3,
            'available_slots': 1
        }
        decision = self.rate_limiter._make_decision(check_result, False)
        self.assertTrue(decision.can_generate)
        self.assertEqual(decision.decision, 'allowed')
    
    def test_pending_decision_when_over_limit(self):
        """测试pending水位超限时的决策"""
        check_result = {
            'can_generate': False,
            'current_pending': 5,
            'max_allowed': 3,
            'available_slots': 0
        }
        decision = self.rate_limiter._make_decision(check_result, False)
        self.assertFalse(decision.can_generate)
        self.assertEqual(decision.decision, 'blocked_pending_watermark')


class TestTitlePrefixDedupV43(unittest.TestCase):
    """标题前缀去重 V4.3 测试"""
    
    def setUp(self):
        self.dedup = TitlePrefixDedupV43(prefix_length=15)
    
    def test_default_prefix_length(self):
        """测试默认前缀长度"""
        self.assertEqual(self.dedup.prefix_length, 15)
    
    def test_extract_prefix_basic(self):
        """测试基本前缀提取"""
        title = "T1: AI助手优化 - 调度系统升级"
        prefix = self.dedup.extract_prefix(title)
        self.assertEqual(len(prefix), 15)
        self.assertEqual(prefix, "T1: AI助手优化 - 调")
    
    def test_extract_prefix_short_title(self):
        """测试短标题前缀提取"""
        title = "短标题"
        prefix = self.dedup.extract_prefix(title)
        self.assertEqual(len(prefix), 3)
        self.assertEqual(prefix, "短标题")
    
    def test_extract_prefix_empty_title(self):
        """测试空标题前缀"""
        prefix = self.dedup.extract_prefix("")
        self.assertEqual(prefix, "")
    
    def test_extract_prefix_with_whitespace(self):
        """测试带空格标题的前缀"""
        title = "   T2: 和光智成商业化   "
        prefix = self.dedup.extract_prefix(title)
        self.assertEqual(len(prefix), 15)
        self.assertEqual(prefix, "T2: 和光智成商业化")
    
    def test_is_duplicate_exact_match(self):
        """测试精确匹配去重"""
        existing = [{"title": "T1: AI助手优化 - 调度系统升级", "id": 1}]
        result = self.dedup.is_duplicate("T1: AI助手优化 - 调度系统升级", 1, existing)
        self.assertIsInstance(result, DedupResult)
        self.assertTrue(result.is_duplicate)
        self.assertEqual(result.matching_task_id, 1)
        self.assertEqual(result.reason, "前缀精确匹配（15字）")
    
    def test_is_duplicate_different_title(self):
        """测试不同标题不重复"""
        existing = [{"title": "T1: AI助手优化 - 调度系统升级", "id": 1}]
        result = self.dedup.is_duplicate("T2: 其他任务", 1, existing)
        self.assertFalse(result.is_duplicate)
    
    def test_is_duplicate_empty_existing(self):
        """测试空现有列表不重复"""
        result = self.dedup.is_duplicate("测试标题", 1, [])
        self.assertFalse(result.is_duplicate)
    
    def test_filter_duplicates_mixed(self):
        """测试混合去重过滤"""
        existing = [
            {"title": "T1: AI助手优化 - 调度系统升级", "id": 1},
            {"title": "T2: 和光智成商业化 - BP更新", "id": 2}
        ]
        candidates = [
            {"title": "T1: AI助手优化 - 调度系统升级V2", "id": 101},  # 重复（前缀相同）
            {"title": "T3: 全新任务类型", "id": 102},  # 不重复
            {"title": "T2: 和光智成商业化 - 融资进展", "id": 103}  # 重复（前缀相同）
        ]
        
        passed, blocked = self.dedup.filter_duplicates(candidates, 1, existing)
        
        self.assertEqual(len(passed), 1)
        self.assertEqual(len(blocked), 2)
        self.assertEqual(passed[0]["title"], "T3: 全新任务类型")


class TestDedupIntegration(unittest.TestCase):
    """集成测试"""
    
    def test_full_dedup_workflow(self):
        """完整去重工作流测试"""
        dedup = TitlePrefixDedupV43(prefix_length=15)
        
        # 模拟已存在的任务
        existing = [
            {"title": "T1: AI助手优化 - 调度系统V4.2", "id": 100},
            {"title": "T2: 和光智成商业化 - 融资BP", "id": 101},
            {"title": "T3: 学术影响力 - 论文发表", "id": 102}
        ]
        
        # 新任务候选
        new_tasks = [
            {"title": "T1: AI助手优化 - 调度系统V4.3", "goal_id": 1},  # 被去重
            {"title": "T2: 和光智成商业化 - 客户拓展", "goal_id": 2},  # 被去重
            {"title": "T4: 财富增值 - AI投资策略", "goal_id": 4},  # 通过
            {"title": "T5: 家庭幸福 - 子女教育规划", "goal_id": 5}  # 通过
        ]
        
        passed, blocked = dedup.filter_duplicates(new_tasks, None, existing)
        
        self.assertEqual(len(passed), 2)
        self.assertEqual(len(blocked), 2)
        self.assertEqual(passed[0]["title"], "T4: 财富增值 - AI投资策略")
        self.assertEqual(passed[1]["title"], "T5: 家庭幸福 - 子女教育规划")


def run_tests():
    """运行所有测试"""
    print("=" * 70)
    print("任务 #2110 交付物：去重机制单元测试 V4.3")
    print("=" * 70)
    
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestRateLimitV43))
    suite.addTests(loader.loadTestsFromTestCase(TestTitlePrefixDedupV43))
    suite.addTests(loader.loadTestsFromTestCase(TestDedupIntegration))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "=" * 70)
    print(f"测试结果: {result.testsRun} 个测试运行")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")
    print("=" * 70)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
