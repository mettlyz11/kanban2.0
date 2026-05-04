#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
任务生成守卫 V4.3 单元测试
覆盖:
1. 频率限制测试（每目标每24小时最多2个任务）
2. 标题去重测试（15字前缀精确匹配）
3. Pending水位控制测试（每目标最多3个pending）
4. 审计日志测试
5. 边界条件测试

任务: #2110 - 调度系统频率限制与去重机制升级
创建日期: 2026-04-28
"""

import os
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

# 添加路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'scripts'))
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.task_generation_guard_v43 import (
    TaskGenerationGuardV43,
    RejectReason,
    GenerationResult,
    can_generate_task_v43,
    record_task_generation_v43
)


class TestTaskGenerationGuardV43(unittest.TestCase):
    """V4.3守卫单元测试"""
    
    def setUp(self):
        """每个测试前的设置"""
        self.guard = TaskGenerationGuardV43(
            max_tasks_per_24h=2,
            max_pending_per_goal=3,
            duplicate_prefix_length=15
        )
    
    def test_initialization(self):
        """测试初始化配置"""
        self.assertEqual(self.guard.max_tasks_per_24h, 2)
        self.assertEqual(self.guard.max_pending_per_goal, 3)
        self.assertEqual(self.guard.duplicate_prefix_length, 15)
    
    @patch('core.task_generation_guard_v43.execute_query')
    def test_frequency_limit_zero_tasks(self, mock_query):
        """测试频率限制: 0个任务，应该允许"""
        # Mock返回0个任务
        mock_query.return_value = [{'count': 0}]
        
        result = self.guard._check_frequency_limit(goal_id=1)
        
        self.assertTrue(result['allowed'])
        self.assertEqual(result['count'], 0)
        self.assertEqual(result['limit'], 2)
    
    @patch('core.task_generation_guard_v43.execute_query')
    def test_frequency_limit_one_task(self, mock_query):
        """测试频率限制: 1个任务，应该允许"""
        mock_query.return_value = [{'count': 1}]
        
        result = self.guard._check_frequency_limit(goal_id=1)
        
        self.assertTrue(result['allowed'])
        self.assertEqual(result['count'], 1)
    
    @patch('core.task_generation_guard_v43.execute_query')
    def test_frequency_limit_two_tasks(self, mock_query):
        """测试频率限制: 2个任务，应该拒绝"""
        mock_query.return_value = [{'count': 2}]
        
        result = self.guard._check_frequency_limit(goal_id=1)
        
        self.assertFalse(result['allowed'])
        self.assertEqual(result['count'], 2)
    
    @patch('core.task_generation_guard_v43.execute_query')
    def test_frequency_limit_three_tasks(self, mock_query):
        """测试频率限制: 3个任务，应该拒绝"""
        mock_query.return_value = [{'count': 3}]
        
        result = self.guard._check_frequency_limit(goal_id=1)
        
        self.assertFalse(result['allowed'])
    
    @patch('core.task_generation_guard_v43.execute_query')
    def test_pending_watermark_zero(self, mock_query):
        """测试Pending水位: 0个任务，应该允许"""
        mock_query.return_value = [{'count': 0}]
        
        result = self.guard._check_pending_watermark(goal_id=1)
        
        self.assertTrue(result['allowed'])
        self.assertEqual(result['count'], 0)
    
    @patch('core.task_generation_guard_v43.execute_query')
    def test_pending_watermark_two(self, mock_query):
        """测试Pending水位: 2个任务，应该允许"""
        mock_query.return_value = [{'count': 2}]
        
        result = self.guard._check_pending_watermark(goal_id=1)
        
        self.assertTrue(result['allowed'])
    
    @patch('core.task_generation_guard_v43.execute_query')
    def test_pending_watermark_three(self, mock_query):
        """测试Pending水位: 3个任务，应该拒绝"""
        mock_query.return_value = [{'count': 3}]
        
        result = self.guard._check_pending_watermark(goal_id=1)
        
        self.assertFalse(result['allowed'])
    
    @patch('core.task_generation_guard_v43.execute_query')
    def test_pending_watermark_five(self, mock_query):
        """测试Pending水位: 5个任务，应该拒绝"""
        mock_query.return_value = [{'count': 5}]
        
        result = self.guard._check_pending_watermark(goal_id=1)
        
        self.assertFalse(result['allowed'])
    
    @patch('core.task_generation_guard_v43.execute_query')
    def test_duplicate_title_no_match(self, mock_query):
        """测试标题去重: 无匹配，应该允许"""
        mock_query.return_value = []
        
        title = "T1: AI助手优化 - 测试新功能"
        result = self.guard._check_duplicate_title(goal_id=1, task_title=title)
        
        self.assertTrue(result['allowed'])
        self.assertEqual(result['prefix'], title[:15])
    
    @patch('core.task_generation_guard_v43.execute_query')
    def test_duplicate_title_match_found(self, mock_query):
        """测试标题去重: 找到匹配，应该拒绝"""
        mock_query.return_value = [{
            'id': 1234,
            'title': "T1: AI助手优化 - 已存在的任务",
            'created_at': datetime.now()
        }]
        
        title = "T1: AI助手优化 - 新任务但前缀相同"
        result = self.guard._check_duplicate_title(goal_id=1, task_title=title)
        
        self.assertFalse(result['allowed'])
        self.assertEqual(result['prefix'], title[:15])
        self.assertEqual(result['duplicate_id'], 1234)
    
    @patch('core.task_generation_guard_v43.execute_query')
    def test_duplicate_title_exact_match(self, mock_query):
        """测试标题去重: 完全相同标题"""
        mock_query.return_value = [{
            'id': 1234,
            'title': "完全相同的标题测试",
            'created_at': datetime.now()
        }]
        
        title = "完全相同的标题测试"
        result = self.guard._check_duplicate_title(goal_id=1, task_title=title)
        
        self.assertFalse(result['allowed'])
    
    @patch('core.task_generation_guard_v43.execute_query')
    def test_duplicate_title_short_title(self, mock_query):
        """测试标题去重: 短标题（小于15字）"""
        mock_query.return_value = [{
            'id': 1234,
            'title': "短标题",
            'created_at': datetime.now()
        }]
        
        title = "短标题"
        result = self.guard._check_duplicate_title(goal_id=1, task_title=title)
        
        self.assertFalse(result['allowed'])
        self.assertEqual(result['prefix'], "短标题")
    
    @patch.object(TaskGenerationGuardV43, '_check_pending_watermark')
    @patch.object(TaskGenerationGuardV43, '_check_frequency_limit')
    @patch.object(TaskGenerationGuardV43, '_check_duplicate_title')
    def test_can_generate_task_all_passed(
        self, mock_dup, mock_freq, mock_pending
    ):
        """测试完整检查: 所有检查通过"""
        mock_pending.return_value = {'allowed': True, 'count': 1}
        mock_freq.return_value = {'allowed': True, 'count': 1}
        mock_dup.return_value = {'allowed': True, 'prefix': 'test'}
        
        result = self.guard.can_generate_task(goal_id=1, task_title="测试任务标题")
        
        self.assertTrue(result.allowed)
        self.assertEqual(result.reason, RejectReason.SUCCESS)
        self.assertIn('可以生成任务', result.message)
    
    @patch.object(TaskGenerationGuardV43, '_check_pending_watermark')
    @patch.object(TaskGenerationGuardV43, '_check_frequency_limit')
    @patch.object(TaskGenerationGuardV43, '_check_duplicate_title')
    def test_can_generate_task_pending_blocked(
        self, mock_dup, mock_freq, mock_pending
    ):
        """测试完整检查: Pending水位阻止"""
        mock_pending.return_value = {'allowed': False, 'count': 5}
        mock_freq.return_value = {'allowed': True, 'count': 1}
        mock_dup.return_value = {'allowed': True, 'prefix': 'test'}
        
        result = self.guard.can_generate_task(goal_id=1, task_title="测试任务标题")
        
        self.assertFalse(result.allowed)
        self.assertEqual(result.reason, RejectReason.PENDING_WATERMARK)
        self.assertIn('Pending任务水位超限', result.message)
    
    @patch.object(TaskGenerationGuardV43, '_check_pending_watermark')
    @patch.object(TaskGenerationGuardV43, '_check_frequency_limit')
    @patch.object(TaskGenerationGuardV43, '_check_duplicate_title')
    def test_can_generate_task_frequency_blocked(
        self, mock_dup, mock_freq, mock_pending
    ):
        """测试完整检查: 频率限制阻止"""
        mock_pending.return_value = {'allowed': True, 'count': 1}
        mock_freq.return_value = {'allowed': False, 'count': 3}
        mock_dup.return_value = {'allowed': True, 'prefix': 'test'}
        
        result = self.guard.can_generate_task(goal_id=1, task_title="测试任务标题")
        
        self.assertFalse(result.allowed)
        self.assertEqual(result.reason, RejectReason.FREQUENCY_LIMIT)
        self.assertIn('生成频率超限', result.message)
    
    @patch.object(TaskGenerationGuardV43, '_check_pending_watermark')
    @patch.object(TaskGenerationGuardV43, '_check_frequency_limit')
    @patch.object(TaskGenerationGuardV43, '_check_duplicate_title')
    def test_can_generate_task_duplicate_blocked(
        self, mock_dup, mock_freq, mock_pending
    ):
        """测试完整检查: 标题重复阻止"""
        mock_pending.return_value = {'allowed': True, 'count': 1}
        mock_freq.return_value = {'allowed': True, 'count': 1}
        mock_dup.return_value = {'allowed': False, 'prefix': 'test_prefix', 'duplicate_id': 123}
        
        result = self.guard.can_generate_task(goal_id=1, task_title="测试任务标题")
        
        self.assertFalse(result.allowed)
        self.assertEqual(result.reason, RejectReason.DUPLICATE_TITLE)
        self.assertIn('标题重复', result.message)
    
    @patch('core.task_generation_guard_v43.execute_update')
    @patch('core.task_generation_guard_v43.execute_query')
    def test_record_task_generation_success(self, mock_query, mock_update):
        """测试记录任务生成: 成功"""
        mock_query.return_value = [{'id': 999}]
        mock_update.return_value = 1
        
        result = self.guard.record_task_generation(
            goal_id=1,
            task_id=12345,
            task_title="测试任务标题"
        )
        
        self.assertTrue(result)
        # 应该调用了两次execute_update（频率表 + 审计表）
        self.assertEqual(mock_update.call_count, 2)
    
    @patch('core.task_generation_guard_v43.execute_update')
    def test_record_task_rejection_success(self, mock_update):
        """测试记录任务拒绝: 成功"""
        mock_update.return_value = 1
        
        result = self.guard.record_task_rejection(
            goal_id=1,
            task_title="被拒绝的任务",
            reason=RejectReason.FREQUENCY_LIMIT,
            details={'count': 3}
        )
        
        self.assertTrue(result)
        mock_update.assert_called_once()
    
    @patch('core.task_generation_guard_v43.execute_update')
    def test_record_task_rejection_failure(self, mock_update):
        """测试记录任务拒绝: 数据库异常"""
        mock_update.side_effect = Exception("DB Error")
        
        result = self.guard.record_task_rejection(
            goal_id=1,
            task_title="被拒绝的任务",
            reason=RejectReason.DUPLICATE_TITLE,
            details={}
        )
        
        self.assertFalse(result)
    
    @patch.object(TaskGenerationGuardV43, '_check_pending_watermark')
    @patch.object(TaskGenerationGuardV43, '_check_frequency_limit')
    def test_get_goal_status_normal(self, mock_freq, mock_pending):
        """测试获取目标状态: 正常情况"""
        mock_pending.return_value = {'allowed': True, 'count': 1, 'limit': 3}
        mock_freq.return_value = {'allowed': True, 'count': 1, 'limit': 2}
        
        status = self.guard.get_goal_status(goal_id=1)
        
        self.assertEqual(status['goal_id'], 1)
        self.assertTrue(status['frequency']['allowed'])
        self.assertTrue(status['pending_tasks']['allowed'])
        self.assertEqual(status['frequency']['remaining'], 1)
        self.assertEqual(status['pending_tasks']['available_slots'], 2)
    
    @patch.object(TaskGenerationGuardV43, '_check_pending_watermark')
    @patch.object(TaskGenerationGuardV43, '_check_frequency_limit')
    @patch('core.task_generation_guard_v43.execute_query')
    def test_get_goal_status_quota_full(self, mock_query, mock_freq, mock_pending):
        """测试获取目标状态: 配额用完"""
        mock_pending.return_value = {'allowed': True, 'count': 1, 'limit': 3}
        mock_freq.return_value = {'allowed': False, 'count': 2, 'limit': 2}
        mock_query.return_value = [{
            'earliest_time': datetime.now() - timedelta(hours=12)
        }]
        
        status = self.guard.get_goal_status(goal_id=1)
        
        self.assertFalse(status['frequency']['allowed'])
        self.assertIsNotNone(status['frequency']['quota_release_time'])
    
    def test_reject_reason_enum(self):
        """测试拒绝原因枚举"""
        self.assertEqual(RejectReason.FREQUENCY_LIMIT.value, 'frequency_limit')
        self.assertEqual(RejectReason.DUPLICATE_TITLE.value, 'duplicate_title')
        self.assertEqual(RejectReason.PENDING_WATERMARK.value, 'pending_watermark')
        self.assertEqual(RejectReason.SUCCESS.value, 'success')
    
    def test_generation_result_structure(self):
        """测试生成结果结构"""
        result = GenerationResult(
            allowed=True,
            reason=RejectReason.SUCCESS,
            message="测试消息",
            details={'test': 'value'}
        )
        
        self.assertTrue(result.allowed)
        self.assertEqual(result.reason, RejectReason.SUCCESS)
        self.assertEqual(result.message, "测试消息")
        self.assertEqual(result.details['test'], 'value')
    
    @patch('core.task_generation_guard_v43.TaskGenerationGuardV43.can_generate_task')
    def test_convenience_function_can_generate(self, mock_method):
        """测试便捷函数 can_generate_task_v43"""
        mock_method.return_value = GenerationResult(
            allowed=True, reason=RejectReason.SUCCESS, message="", details={}
        )
        
        result = can_generate_task_v43(goal_id=1, task_title="测试")
        
        self.assertTrue(result.allowed)
        mock_method.assert_called_once_with(1, "测试")
    
    @patch('core.task_generation_guard_v43.TaskGenerationGuardV43.record_task_generation')
    def test_convenience_function_record(self, mock_method):
        """测试便捷函数 record_task_generation_v43"""
        mock_method.return_value = True
        
        result = record_task_generation_v43(goal_id=1, task_id=123, task_title="测试")
        
        self.assertTrue(result)
        mock_method.assert_called_once_with(1, 123, "测试")
    
    def test_custom_config_values(self):
        """测试自定义配置值"""
        custom_guard = TaskGenerationGuardV43(
            max_tasks_per_24h=5,
            max_pending_per_goal=10,
            duplicate_prefix_length=20,
            window_hours=48
        )
        
        self.assertEqual(custom_guard.max_tasks_per_24h, 5)
        self.assertEqual(custom_guard.max_pending_per_goal, 10)
        self.assertEqual(custom_guard.duplicate_prefix_length, 20)
        self.assertEqual(custom_guard.window_hours, 48)


class TestBoundaryConditions(unittest.TestCase):
    """边界条件测试"""
    
    def setUp(self):
        self.guard = TaskGenerationGuardV43(
            max_tasks_per_24h=2,
            max_pending_per_goal=3,
            duplicate_prefix_length=15
        )
    
    @patch('core.task_generation_guard_v43.execute_query')
    def test_frequency_boundary_exactly_limit_minus_1(self, mock_query):
        """边界测试: 刚好等于 limit-1"""
        mock_query.return_value = [{'count': 1}]  # limit=2, so 2-1=1
        
        result = self.guard._check_frequency_limit(goal_id=1)
        self.assertTrue(result['allowed'])
    
    @patch('core.task_generation_guard_v43.execute_query')
    def test_frequency_boundary_exactly_limit(self, mock_query):
        """边界测试: 刚好等于 limit"""
        mock_query.return_value = [{'count': 2}]  # 等于limit
        
        result = self.guard._check_frequency_limit(goal_id=1)
        self.assertFalse(result['allowed'])
    
    @patch('core.task_generation_guard_v43.execute_query')
    def test_pending_boundary_exactly_limit_minus_1(self, mock_query):
        """边界测试: Pending刚好等于 limit-1"""
        mock_query.return_value = [{'count': 2}]  # limit=3, so 3-1=2
        
        result = self.guard._check_pending_watermark(goal_id=1)
        self.assertTrue(result['allowed'])
    
    @patch('core.task_generation_guard_v43.execute_query')
    def test_pending_boundary_exactly_limit(self, mock_query):
        """边界测试: Pending刚好等于 limit"""
        mock_query.return_value = [{'count': 3}]  # 等于limit
        
        result = self.guard._check_pending_watermark(goal_id=1)
        self.assertFalse(result['allowed'])
    
    @patch('core.task_generation_guard_v43.execute_query')
    def test_duplicate_boundary_exact_15_chars(self, mock_query):
        """边界测试: 标题刚好15字符完全匹配"""
        mock_query.return_value = [{
            'id': 123,
            'title': "123456789012345",  # 15 characters
            'created_at': datetime.now()
        }]
        
        title = "123456789012345"  # exactly 15 chars
        result = self.guard._check_duplicate_title(goal_id=1, task_title=title)
        
        self.assertFalse(result['allowed'])
        self.assertEqual(len(result['prefix']), 15)
    
    @patch('core.task_generation_guard_v43.execute_query')
    def test_duplicate_boundary_14_chars_match(self, mock_query):
        """边界测试: 标题小于15字符完全匹配"""
        mock_query.return_value = [{
            'id': 123,
            'title': "12345678901234",  # 14 characters
            'created_at': datetime.now()
        }]
        
        title = "12345678901234"  # 14 chars
        result = self.guard._check_duplicate_title(goal_id=1, task_title=title)
        
        self.assertFalse(result['allowed'])
        self.assertEqual(len(result['prefix']), 14)
    
    @patch('core.task_generation_guard_v43.execute_query')
    def test_empty_title_handling(self, mock_query):
        """边界测试: 空标题"""
        mock_query.return_value = []
        
        result = self.guard._check_duplicate_title(goal_id=1, task_title="")
        
        self.assertTrue(result['allowed'])
        self.assertEqual(result['prefix'], "")
    
    @patch('core.task_generation_guard_v43.execute_query')
    def test_very_long_title_handling(self, mock_query):
        """边界测试: 非常长的标题"""
        mock_query.return_value = []
        
        long_title = "A" * 1000  # 1000 character title
        result = self.guard._check_duplicate_title(goal_id=1, task_title=long_title)
        
        self.assertTrue(result['allowed'])
        self.assertEqual(len(result['prefix']), 15)  # should only take first 15 chars


def run_tests():
    """运行所有测试并生成报告"""
    print("=" * 70)
    print("  SDS v4.3 任务生成守卫 - 单元测试")
    print("=" * 70)
    print()
    
    # 创建测试套件
    loader = unittest.TestLoader()
    suite1 = loader.loadTestsFromTestCase(TestTaskGenerationGuardV43)
    suite2 = loader.loadTestsFromTestCase(TestBoundaryConditions)
    full_suite = unittest.TestSuite([suite1, suite2])
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(full_suite)
    
    # 生成测试报告
    print()
    print("=" * 70)
    print("  测试结果总结")
    print("=" * 70)
    print(f"  运行测试数: {result.testsRun}")
    print(f"  成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"  失败: {len(result.failures)}")
    print(f"  错误: {len(result.errors)}")
    print()
    
    if result.failures:
        print("  失败的测试:")
        for test, traceback in result.failures:
            print(f"    ❌ {str(test)}")
    
    if result.errors:
        print("  错误的测试:")
        for test, traceback in result.errors:
            print(f"    ❌ {str(test)}")
    
    print()
    if result.wasSuccessful():
        print("  ✅ 所有测试通过！")
    else:
        print("  ❌ 部分测试失败，请检查代码")
    print("=" * 70)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
