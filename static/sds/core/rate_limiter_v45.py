#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SDS调度系统V4.3单元测试 - 任务 #2110交付物

测试覆盖：
1. ✅ 频率限制测试
2. ✅ Pending水位控制测试
3. ✅ 前缀去重测试
4. ✅ 语义相似度测试
5. ✅ Levenshtein编辑距离测试
6. ✅ 集成测试

运行方式：
  python -m pytest test_scheduler_v43.py -v
  python test_scheduler_v43.py
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict
import unittest
from unittest.mock import patch, MagicMock

# 添加路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

# 导入被测试模块
from scheduler_v43_complete import (
    RateLimitLayer,
    DeduplicationLayer,
    SDSV43Scheduler,
    TaskGenerationCheckResult
)


class TestLevenshteinDistance(unittest.TestCase):
    """测试Levenshtein编辑距离算法"""
    
    def test_identical_strings(self):
        """相同字符串距离应为0"""
        self.assertEqual(DeduplicationLayer.levenshtein_distance("abc", "abc"), 0)
        self.assertEqual(DeduplicationLayer.levenshtein_distance("", ""), 0)
        self.assertEqual(DeduplicationLayer.levenshtein_distance("和光智成", "和光智成"), 0)
    
    def test_one_char_different(self):
        """一个字符不同"""
        # 插入
        self.assertEqual(DeduplicationLayer.levenshtein_distance("abc", "abcd"), 1)
        # 删除
        self.assertEqual(DeduplicationLayer.levenshtein_distance("abcd", "abc"), 1)
        # 替换
        self.assertEqual(DeduplicationLayer.levenshtein_distance("abc", "adc"), 1)
    
    def test_chinese_strings(self):
        """中文字符串测试"""
        self.assertEqual(DeduplicationLayer.levenshtein_distance("法务纠纷处理", "法务纠纷处理"), 0)
        self.assertEqual(DeduplicationLayer.levenshtein_distance("法务纠纷处理", "法务纠纷整理"), 2)


class TestStringSimilarity(unittest.TestCase):
    """测试字符串相似度计算"""
    
    def test_identical_similarity(self):
        """完全相同应为1.0"""
        self.assertAlmostEqual(DeduplicationLayer.string_similarity("test", "test"), 1.0)
        self.assertAlmostEqual(DeduplicationLayer.string_similarity("", ""), 1.0)
    
    def test_partial_similarity(self):
        """部分相似"""
        # 只差一个字符，相似度应该很高
        sim = DeduplicationLayer.string_similarity("Hello World", "Hello world")
        self.assertGreater(sim, 0.8)
    
    def test_chinese_similarity(self):
        """中文相似度测试"""
        s1 = "T1: 法务纠纷处理 - 包头九原区法院案件"
        s2 = "T1: 法务纠纷处理 - 包头九原区法院证据"
        sim = DeduplicationLayer.string_similarity(s1, s2)
        self.assertGreater(sim, 0.85)  # 应该超过去重阈值
    
    def test_different_strings(self):
        """完全不同的字符串"""
        sim = DeduplicationLayer.string_similarity("法务纠纷处理", "AI助手优化")
        self.assertLess(sim, 0.5)


class TestTextNormalization(unittest.TestCase):
    """测试文本标准化"""
    
    def test_normalize_lowercase(self):
        """转小写"""
        self.assertEqual(DeduplicationLayer.normalize_text("HELLO WORLD"), "helloworld")
    
    def test_normalize_remove_punctuation(self):
        """移除标点符号"""
        self.assertEqual(DeduplicationLayer.normalize_text("Hello, World!"), "helloworld")
        self.assertEqual(DeduplicationLayer.normalize_text("T1: 测试-任务！"), "t1测试任务")
        self.assertEqual(DeduplicationLayer.normalize_text("【重要】紧急任务"), "重要紧急任务")
    
    def test_normalize_chinese(self):
        """中文标准化"""
        text = "和光智成-商业化融资BP更新"
        normalized = DeduplicationLayer.normalize_text(text)
        self.assertNotIn("-", normalized)
        self.assertIn("和光智成", normalized)


class TestRateLimitLayer(unittest.TestCase):
    """测试频率限制层"""
    
    def test_rate_limit_init(self):
        """初始化测试"""
        rl = RateLimitLayer(max_tasks_per_24h=2, max_pending_per_goal=3)
        self.assertEqual(rl.max_tasks_per_24h, 2)
        self.assertEqual(rl.max_pending_per_goal, 3)
    
    @patch('scheduler_v43_complete.execute_query')
    def test_rate_limit_within_limit(self, mock_query):
        """在限制内应该允许生成"""
        mock_query.return_value = [{'cnt': 1}]
        rl = RateLimitLayer(max_tasks_per_24h=2)
        can_generate, details = rl.check_rate_limit(goal_id=1)
        self.assertTrue(can_generate)
        self.assertEqual(details['current_count'], 1)
        self.assertEqual(details['remaining_slots'], 1)
    
    @patch('scheduler_v43_complete.execute_query')
    def test_rate_limit_exceeded(self, mock_query):
        """超过限制应该阻止"""
        mock_query.return_value = [{'cnt': 3}]
        rl = RateLimitLayer(max_tasks_per_24h=2)
        can_generate, details = rl.check_rate_limit(goal_id=1)
        self.assertFalse(can_generate)
        self.assertEqual(details['current_count'], 3)
        self.assertEqual(details['remaining_slots'], 0)
    
    @patch('scheduler_v43_complete.execute_query')
    def test_rate_limit_exactly_at_limit(self, mock_query):
        """刚好达到限制"""
        mock_query.return_value = [{'cnt': 2}]
        rl = RateLimitLayer(max_tasks_per_24h=2)
        can_generate, details = rl.check_rate_limit(goal_id=1)
        self.assertFalse(can_generate)
    
    @patch('scheduler_v43_complete.execute_query')
    def test_pending_watermark_within_limit(self, mock_query):
        """Pending在限制内"""
        mock_query.return_value = [{'cnt': 2}]
        rl = RateLimitLayer(max_pending_per_goal=3)
        can_generate, details = rl.check_pending_watermark(goal_id=1)
        self.assertTrue(can_generate)
        self.assertEqual(details['current_pending'], 2)
        self.assertEqual(details['available_slots'], 1)
    
    @patch('scheduler_v43_complete.execute_query')
    def test_pending_watermark_exceeded(self, mock_query):
        """Pending超过限制"""
        mock_query.return_value = [{'cnt': 4}]
        rl = RateLimitLayer(max_pending_per_goal=3)
        can_generate, details = rl.check_pending_watermark(goal_id=1)
        self.assertFalse(can_generate)
        self.assertEqual(details['current_pending'], 4)
        self.assertEqual(details['available_slots'], 0)


class TestDeduplicationLayer(unittest.TestCase):
    """测试去重层"""
    
    def test_dedup_init(self):
        """初始化测试"""
        dedup = DeduplicationLayer(prefix_length=15, similarity_threshold=0.85)
        self.assertEqual(dedup.prefix_length, 15)
        self.assertEqual(dedup.similarity_threshold, 0.85)
    
    @patch('scheduler_v43_complete.execute_query')
    def test_prefix_duplicate_detection(self, mock_query):
        """前缀重复检测 - 15字前缀匹配"""
        # 模拟数据库返回匹配结果
        mock_query.return_value = [
            {
                'id': 123,
                'title': 'T1: 法务纠纷处理 - 包头九原区法院案件证据清单',
                'status': 'pending',
                'goal_id': 1,
                'created_at': datetime.now()
            }
        ]
        
        dedup = DeduplicationLayer(prefix_length=15)
        new_title = 'T1: 法务纠纷处理 - 包头九原区法院案件证据清单更新'
        
        is_unique, details = dedup.check_duplicate(new_title, goal_id=1)
        
        # 前缀相同，应该判定为重复
        self.assertFalse(is_unique)
        self.assertEqual(details['match_type'], 'prefix')
        self.assertEqual(len(details['matched_tasks']), 1)
        self.assertEqual(details['matched_tasks'][0]['id'], 123)
    
    @patch('scheduler_v43_complete.execute_query')
    def test_no_duplicate(self, mock_query):
        """无重复情况"""
        # 第一次前缀查询返回空
        # 第二次语义查询返回不相似的任务
        def side_effect(*args, **kwargs):
            return [
                {
                    'id': 999,
                    'title': '完全不同的任务标题',
                    'status': 'completed',
                    'goal_id': 1,
                    'created_at': datetime.now()
                }
            ]
        
        mock_query.side_effect = [[], side_effect()]
        
        dedup = DeduplicationLayer(prefix_length=15)
        new_title = '全新的独一无二的任务标题'
        
        is_unique, details = dedup.check_duplicate(new_title, goal_id=1)
        
        self.assertTrue(is_unique)
        self.assertEqual(details['match_type'], 'none')
    
    @patch('scheduler_v43_complete.execute_query')
    def test_semantic_duplicate_detection(self, mock_query):
        """语义重复检测"""
        # 前缀查询返回空
        # 语义查询返回相似任务
        def side_effect(*args, **kwargs):
            return [
                {
                    'id': 456,
                    'title': 'T2: 和光智成商业化融资计划书更新版本',
                    'status': 'pending',
                    'goal_id': 2,
                    'created_at': datetime.now()
                }
            ]
        
        mock_query.side_effect = [[], side_effect()]
        
        dedup = DeduplicationLayer(prefix_length=15, similarity_threshold=0.8)
        new_title = 'T2: 和光智成商业化融资BP更新'
        
        is_unique, details = dedup.check_duplicate(new_title, goal_id=2)
        
        # 语义相似，应该判定为重复
        self.assertFalse(is_unique)
        self.assertEqual(details['match_type'], 'semantic')


class TestSDSV43SchedulerIntegration(unittest.TestCase):
    """SDS V4.3调度器集成测试"""
    
    @patch('scheduler_v43_complete.execute_update')
    @patch('scheduler_v43_complete.execute_query')
    def test_full_check_all_passed(self, mock_query, mock_update):
        """所有检查都通过"""
        # 模拟数据库返回
        def side_effect(*args, **kwargs):
            return []
        
        mock_query.side_effect = [
            [{'cnt': 1}],  # rate limit check: 1 < 2, OK
            [{'cnt': 2}],  # pending check: 2 < 3, OK
            [],  # prefix dedup: no match
            [],  # semantic dedup: no match
        ]
        mock_update.return_value = 1
        
        scheduler = SDSV43Scheduler()
        
        result = scheduler.can_generate_task(goal_id=1, title='全新的测试任务标题')
        
        self.assertTrue(result.can_generate)
        self.assertTrue(result.rate_limit_passed)
        self.assertTrue(result.pending_watermark_passed)
        self.assertTrue(result.deduplication_passed)
        self.assertEqual(result.final_decision, 'allowed')
    
    @patch('scheduler_v43_complete.execute_update')
    @patch('scheduler_v43_complete.execute_query')
    def test_full_check_rate_blocked(self, mock_query, mock_update):
        """频率限制阻止"""
        mock_query.side_effect = [
            [{'cnt': 3}],  # rate limit check: 3 > 2, BLOCKED
        ]
        mock_update.return_value = 1
        
        scheduler = SDSV43Scheduler()
        
        result = scheduler.can_generate_task(goal_id=1, title='测试任务')
        
        self.assertFalse(result.can_generate)
        self.assertFalse(result.rate_limit_passed)
        self.assertIsNone(result.pending_watermark_passed)
        self.assertIsNone(result.deduplication_passed)
        self.assertEqual(result.final_decision, 'blocked_rate_limit')
    
    @patch('scheduler_v43_complete.execute_update')
    @patch('scheduler_v43_complete.execute_query')
    def test_full_check_pending_blocked(self, mock_query, mock_update):
        """Pending水位阻止"""
        mock_query.side_effect = [
            [{'cnt': 1}],  # rate limit: OK
            [{'cnt': 4}],  # pending: 4 > 3, BLOCKED
        ]
        mock_update.return_value = 1
        
        scheduler = SDSV43Scheduler()
        
        result = scheduler.can_generate_task(goal_id=1, title='测试任务')
        
        self.assertFalse(result.can_generate)
        self.assertTrue(result.rate_limit_passed)
        self.assertFalse(result.pending_watermark_passed)
        self.assertIsNone(result.deduplication_passed)
        self.assertEqual(result.final_decision, 'blocked_pending_watermark')
    
    @patch('scheduler_v43_complete.execute_update')
    @patch('scheduler_v43_complete.execute_query')
    def test_full_check_dup_blocked(self, mock_query, mock_update):
        """去重阻止"""
        mock_query.side_effect = [
            [{'cnt': 1}],  # rate limit: OK
            [{'cnt': 2}],  # pending: OK
            [{  # prefix match: FOUND
                'id': 123,
                'title': '测试任务标题前缀匹配',
                'status': 'pending',
                'goal_id': 1,
                'created_at': datetime.now()
            }],
        ]
        mock_update.return_value = 1
        
        scheduler = SDSV43Scheduler()
        
        result = scheduler.can_generate_task(goal_id=1, title='测试任务标题前缀匹配扩展版')
        
        self.assertFalse(result.can_generate)
        self.assertTrue(result.rate_limit_passed)
        self.assertTrue(result.pending_watermark_passed)
        self.assertFalse(result.deduplication_passed)
        self.assertEqual(result.final_decision, 'blocked_duplicate')
    
    @patch('scheduler_v43_complete.execute_update')
    @patch('scheduler_v43_complete.execute_query')
    def test_get_system_status(self, mock_query, mock_update):
        """获取系统状态"""
        # 为每个目标模拟返回
        def side_effect(*args, **kwargs):
            return [{'cnt': 1}]
        
        mock_query.side_effect = [
            [{'cnt': 1}], [{'cnt': 1}],  # goal 1
            [{'cnt': 1}], [{'cnt': 1}],  # goal 2
            [{'cnt': 1}], [{'cnt': 1}],  # goal 3
            [{'cnt': 1}], [{'cnt': 1}],  # goal 4
            [{'cnt': 1}], [{'cnt': 1}],  # goal 5
            [{'cnt': 1}], [{'cnt': 1}],  # goal 6
            [{'cnt': 1}], [{'cnt': 1}],  # goal 7
            []  # audit stats
        ]
        mock_update.return_value = 1
        
        scheduler = SDSV43Scheduler()
        status = scheduler.get_system_status()
        
        self.assertEqual(status['version'], 'V4.3')
        self.assertIn('goals', status)
        self.assertEqual(len(status['goals']), 7)
        self.assertIn('audit_stats', status)


class TestResultDataStructures(unittest.TestCase):
    """测试数据结构"""
    
    def test_task_generation_check_result(self):
        """测试检查结果数据结构"""
        result = TaskGenerationCheckResult(
            can_generate=True,
            goal_id=1,
            title='测试任务',
            rate_limit_passed=True,
            rate_limit_details={'current_count': 1},
            pending_watermark_passed=True,
            pending_watermark_details={'current_pending': 1},
            deduplication_passed=True,
            deduplication_details={'match_type': 'none'},
            final_decision='allowed',
            decision_reason='所有检查通过',
            check_timestamp=datetime.now().isoformat()
        )
        
        d = result.to_dict()
        self.assertEqual(d['can_generate'], True)
        self.assertEqual(d['goal_id'], 1)
        self.assertEqual(d['final_decision'], 'allowed')


# 运行测试
def run_tests():
    """运行所有测试并输出报告"""
    # print("=" * 70)
    # print("  SDS调度系统V4.3 - 单元测试")
    # print("=" * 70)
    
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加所有测试类
    test_classes = [
        TestLevenshteinDistance,
        TestStringSimilarity,
        TestTextNormalization,
        TestRateLimitLayer,
        TestDeduplicationLayer,
        TestSDSV43SchedulerIntegration,
        TestResultDataStructures
    ]
    
    for test_class in test_classes:
        tests = loader.loadTestsFromTestCase(test_class)
        suite.addTests(tests)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 输出总结
    # print("\n" + "=" * 70)
    # print("  测试总结")
    # print("=" * 70)
    # print(f"  运行测试数: {result.testsRun}")
    # print(f"  失败: {len(result.failures)}")
    # print(f"  错误: {len(result.errors)}")
    # print(f"  跳过: {len(result.skipped)}")
    
    if result.wasSuccessful():
        # print("  ✅ 所有测试通过!")
        return 0
    else:
        # print("  ❌ 部分测试失败!")
        return 1


if __name__ == "__main__":
    sys.exit(run_tests())
