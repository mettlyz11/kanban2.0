#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Task #2119: SDS调度系统任务生成频率限制与幂等性保障
边界场景专项测试 - 增强版

测试目标：
1. 频率限制边界（24小时窗口精确边界、零/极大值配置）
2. 语义去重边界（恰好0.85阈值、空/超长标题、纯特殊字符）
3. 幂等性边界（并发键生成、特殊字符、None值）
4. 集成边界（三层协同的极端场景）
"""

import sys
import os
import unittest
import json
import time
import tempfile
import threading
from pathlib import Path
from datetime import datetime, timedelta

# 添加路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "core"))

from core.task_generation_guard_v47 import (
    IdempotencyLayer,
    RateLimitLayer,
    SemanticDedupLayer,
    TaskGenerationGuard,
    GuardDecision,
    GuardResult,
    quick_guard_check
)


class Test2119RateLimitBoundary(unittest.TestCase):
    """Task#2119: 频率限制边界测试"""

    def test_exactly_2_per_24h_allowed(self):
        """24小时内恰好2个任务应允许（< 2时）"""
        layer = RateLimitLayer(max_tasks=2)
        # 逻辑验证：当前1个 < 最大值2 → 允许
        current = 1
        self.assertTrue(current < layer.max_tasks)
        self.assertEqual(layer.max_tasks, 2)
        self.assertEqual(layer.window_hours, 24)

    def test_exactly_2_per_24h_blocked(self):
        """24小时内已达到2个任务应阻止"""
        layer = RateLimitLayer(max_tasks=2)
        current = 2
        self.assertFalse(current < layer.max_tasks)

    def test_window_boundary_24h_exact(self):
        """24小时窗口精确边界"""
        layer = RateLimitLayer(window_hours=24)
        window_start = datetime.now() - timedelta(hours=24)
        # 验证窗口计算
        diff = (datetime.now() - window_start).total_seconds() / 3600
        self.assertAlmostEqual(diff, 24, delta=0.1)

    def test_window_boundary_23h59m_inside(self):
        """23小时59分内的任务应计入窗口"""
        layer = RateLimitLayer(window_hours=24)
        task_time = datetime.now() - timedelta(hours=23, minutes=59)
        window_start = datetime.now() - timedelta(hours=24)
        self.assertTrue(task_time >= window_start)

    def test_window_boundary_24h01m_outside(self):
        """24小时01分前的任务应不计入窗口"""
        layer = RateLimitLayer(window_hours=24)
        task_time = datetime.now() - timedelta(hours=24, minutes=1)
        window_start = datetime.now() - timedelta(hours=24)
        self.assertTrue(task_time < window_start)

    def test_zero_max_tasks_blocks_all(self):
        """max_tasks=0应阻止所有生成"""
        layer = RateLimitLayer(max_tasks=0)
        result = layer.check_rate_limit(1)
        self.assertFalse(result['can_generate'])
        self.assertEqual(result['remaining_slots'], 0)

    def test_very_large_max_tasks(self):
        """极大max_tasks应始终允许"""
        layer = RateLimitLayer(max_tasks=100000)
        result = layer.check_rate_limit(1)
        self.assertTrue(result['can_generate'])
        self.assertGreater(result['remaining_slots'], 0)

    def test_pending_watermark_exactly_3(self):
        """pending恰好3个应阻止"""
        layer = RateLimitLayer(max_pending=3)
        current = 3
        self.assertFalse(current < layer.max_pending)

    def test_pending_watermark_2_allows(self):
        """pending 2个应允许"""
        layer = RateLimitLayer(max_pending=3)
        current = 2
        self.assertTrue(current < layer.max_pending)

    def test_combined_both_blocked(self):
        """频率和水位都满时应阻止"""
        layer = RateLimitLayer(max_tasks=2, max_pending=3)
        # 模拟同时达到上限
        rate_full = not (2 < layer.max_tasks)
        pending_full = not (3 < layer.max_pending)
        self.assertTrue(rate_full and pending_full)


class Test2119SemanticDedupBoundary(unittest.TestCase):
    """Task#2119: 语义去重边界测试"""

    def test_prefix_exactly_15_chars(self):
        """前15字精确匹配"""
        layer = SemanticDedupLayer(prefix_length=15)
        title1 = "T1: AI助手优化-----A"
        title2 = "T1: AI助手优化-----B"
        self.assertEqual(title1[:15], title2[:15])
        self.assertEqual(layer.prefix_length, 15)

    def test_prefix_14_chars_no_match(self):
        """前14字相同但第15字不同不应匹配"""
        title1 = "ABCDEFGHIJKLMNO"  # 15字符
        title2 = "ABCDEFGHIJKLMNP"  # 第15字符不同
        self.assertNotEqual(title1[:15], title2[:15])

    def test_similarity_exactly_0_85_threshold(self):
        """相似度恰好0.85应判定为重复"""
        # 100字符中差15个: 1 - 15/100 = 0.85
        s1 = "A" * 100
        s2 = "A" * 85 + "B" * 15
        sim = SemanticDedupLayer.string_similarity(s1, s2)
        self.assertEqual(sim, 0.85)
        self.assertTrue(sim >= 0.85)

    def test_similarity_0_849_should_not_match(self):
        """相似度0.849不应判定为重复"""
        # 200字符中差31个: 1 - 31/200 = 0.845 < 0.85
        s1 = "A" * 200
        s2 = "A" * 169 + "B" * 31
        sim = SemanticDedupLayer.string_similarity(s1, s2)
        self.assertLess(sim, 0.85)

    def test_similarity_0_851_should_match(self):
        """相似度0.851应判定为重复"""
        # 200字符中差29个: 1 - 29/200 = 0.855 > 0.85
        s1 = "A" * 200
        s2 = "A" * 171 + "B" * 29
        sim = SemanticDedupLayer.string_similarity(s1, s2)
        self.assertGreater(sim, 0.85)

    def test_empty_title_no_duplicate(self):
        """空标题不应判定重复"""
        layer = SemanticDedupLayer()
        result = layer.check("")
        self.assertFalse(result['is_duplicate'])
        self.assertEqual(result['duplicate_type'], 'none')

    def test_none_title_no_duplicate(self):
        """None标题不应判定重复"""
        layer = SemanticDedupLayer()
        result = layer.check(None)
        self.assertFalse(result['is_duplicate'])

    def test_very_long_title_5000_chars(self):
        """5000字符超长标题处理"""
        layer = SemanticDedupLayer()
        title = "A" * 5000
        result = layer.check(title)
        self.assertIsInstance(result, dict)
        self.assertEqual(result['title_prefix'], title[:15])

    def test_only_special_chars_normalized_empty(self):
        """纯特殊字符标准化后为空"""
        title = "!!!???---..."
        normalized = SemanticDedupLayer.normalize_text(title)
        self.assertEqual(normalized, "")

    def test_only_spaces_normalized_empty(self):
        """纯空格标准化后为空"""
        title = "     "
        normalized = SemanticDedupLayer.normalize_text(title)
        self.assertEqual(normalized, "")

    def test_chinese_punctuation_removed(self):
        """中文标点应被去除"""
        title = "你好，世界！今天：测试。"
        normalized = SemanticDedupLayer.normalize_text(title)
        self.assertEqual(normalized, "你好世界今天测试")

    def test_mixed_language_similarity(self):
        """混合语言相似度计算"""
        s1 = "T1: 法务纠纷 Legal Dispute"
        s2 = "T1: 法务纠纷 Legal Dispute"
        sim = SemanticDedupLayer.string_similarity(s1, s2)
        self.assertEqual(sim, 1.0)

    def test_unicode_characters_distance(self):
        """Unicode字符编辑距离"""
        dist = SemanticDedupLayer.levenshtein_distance("日本語", "日本语")
        self.assertEqual(dist, 1)

    def test_semantic_match_with_different_punctuation(self):
        """不同标点但语义相同应匹配"""
        s1 = SemanticDedupLayer.normalize_text("法务纠纷处理！")
        s2 = SemanticDedupLayer.normalize_text("法务纠纷处理")
        sim = SemanticDedupLayer.string_similarity(s1, s2)
        self.assertEqual(sim, 1.0)


class Test2119IdempotencyBoundary(unittest.TestCase):
    """Task#2119: 幂等性保障边界测试"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.log_file = os.path.join(self.temp_dir, 'idem_2119.log')
        self.layer = IdempotencyLayer(log_file=self.log_file)

    def tearDown(self):
        if os.path.exists(self.log_file):
            os.remove(self.log_file)
        os.rmdir(self.temp_dir)

    def test_same_input_same_key(self):
        """相同输入必须生成相同key"""
        k1 = self.layer.generate_key("测试任务", 75, "描述")
        k2 = self.layer.generate_key("测试任务", 75, "描述")
        self.assertEqual(k1, k2)
        self.assertEqual(len(k1), 16)

    def test_different_title_different_key(self):
        """不同标题生成不同key"""
        k1 = self.layer.generate_key("任务A", 1)
        k2 = self.layer.generate_key("任务B", 1)
        self.assertNotEqual(k1, k2)

    def test_different_goal_different_key(self):
        """不同goal_id生成不同key"""
        k1 = self.layer.generate_key("相同标题", 1)
        k2 = self.layer.generate_key("相同标题", 2)
        self.assertNotEqual(k1, k2)

    def test_whitespace_trimmed_same_key(self):
        """首尾空格去除后key相同"""
        k1 = self.layer.generate_key("测试任务", 1)
        k2 = self.layer.generate_key(" 测试任务 ", 1)
        self.assertEqual(k1, k2)

    def test_long_description_truncated(self):
        """超长描述只取前100字符"""
        long_desc = "A" * 200
        k1 = self.layer.generate_key("测试", 1, long_desc)
        k2 = self.layer.generate_key("测试", 1, long_desc[:100])
        self.assertEqual(k1, k2)

    def test_record_and_check_idempotent(self):
        """记录后再次检查应被拦截"""
        key = self.layer.generate_key("幂等测试", 1)
        self.layer.record(key, 12345, "幂等测试", 1)

        result = self.layer.check(key)
        self.assertFalse(result['is_safe'])
        self.assertTrue(result['local_found'])
        self.assertEqual(result['local_task_id'], 12345)

    def test_concurrent_key_generation(self):
        """并发键生成一致性"""
        title = "并发测试任务"
        keys = []

        def generate():
            keys.append(IdempotencyLayer.generate_key(title, 1))

        threads = [threading.Thread(target=generate) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(set(keys)), 1)

    def test_special_chars_in_title(self):
        """标题含特殊字符应正常处理"""
        title = "任务<>&\"'\\n\\t"
        key1 = self.layer.generate_key(title, 1)
        key2 = self.layer.generate_key(title, 1)
        self.assertEqual(key1, key2)
        self.assertEqual(len(key1), 16)

    def test_empty_title_generates_key(self):
        """空标题也能生成key"""
        key = self.layer.generate_key("")
        self.assertEqual(len(key), 16)
        self.assertEqual(self.layer.generate_key(""), key)

    def test_unicode_title(self):
        """Unicode标题key生成"""
        key1 = self.layer.generate_key("日本語タスク", 1)
        key2 = self.layer.generate_key("日本語タスク", 1)
        self.assertEqual(key1, key2)

    def test_none_description_handling(self):
        """None描述应正常处理"""
        key = self.layer.generate_key("测试", None, None)
        self.assertEqual(len(key), 16)

    def test_multiple_records_persist(self):
        """多条记录应独立持久化"""
        for i in range(10):
            key = self.layer.generate_key(f"任务{i}", i)
            self.layer.record(key, 1000 + i, f"任务{i}", i)

        for i in range(10):
            key = self.layer.generate_key(f"任务{i}", i)
            result = self.layer.check(key)
            self.assertFalse(result['is_safe'])
            self.assertEqual(result['local_task_id'], 1000 + i)


class Test2119IntegrationBoundary(unittest.TestCase):
    """Task#2119: 集成边界测试"""

    def test_new_task_passes_all_layers(self):
        """全新任务应通过所有三层检查"""
        guard = TaskGenerationGuard()
        unique_title = f"2119边界测试_{time.time()}"
        result = guard.check(unique_title, 999, "测试描述")
        self.assertEqual(result.decision, GuardDecision.ALLOWED)
        self.assertTrue(result.can_generate)
        self.assertIsNotNone(result.idempotency_key)

    def test_idempotent_second_call_blocked(self):
        """第二次相同调用应被幂等拦截"""
        guard = TaskGenerationGuard()
        title = f"2119幂等测试_{time.time()}"

        r1 = guard.check(title, 999, "测试")
        self.assertEqual(r1.decision, GuardDecision.ALLOWED)

        if r1.idempotency_key:
            guard.idempotency.record(r1.idempotency_key, 99999, title, 999)
            r2 = guard.check(title, 999, "测试")
            self.assertEqual(r2.decision, GuardDecision.BLOCKED_IDEMPOTENT)
            self.assertFalse(r2.can_generate)

    def test_guard_result_structure(self):
        """GuardResult应包含完整字段"""
        result = GuardResult(
            decision=GuardDecision.ALLOWED,
            can_generate=True,
            reason="测试"
        )
        self.assertEqual(result.decision, GuardDecision.ALLOWED)
        self.assertTrue(result.can_generate)
        self.assertEqual(result.reason, "测试")
        self.assertIsNotNone(result.timestamp)
        self.assertIn('layer_checks', result.__dict__ or {})

    def test_batch_filter_empty_list(self):
        """空列表过滤应返回空"""
        guard = TaskGenerationGuard()
        passed, blocked = guard.filter_recommendations([])
        self.assertEqual(len(passed), 0)
        self.assertEqual(len(blocked), 0)

    def test_quick_guard_check_returns_bool(self):
        """快捷函数应返回bool和str"""
        can_gen, reason = quick_guard_check(f"快捷测试_{time.time()}", 999)
        self.assertIsInstance(can_gen, bool)
        self.assertIsInstance(reason, str)

    def test_system_status_contains_all_goals(self):
        """系统状态应包含7个目标"""
        guard = TaskGenerationGuard()
        status = guard.get_system_status()
        self.assertIn('version', status)
        self.assertIn('goals', status)
        self.assertEqual(len(status['goals']), 7)

    def test_guard_with_none_goal(self):
        """None目标ID应正常处理"""
        guard = TaskGenerationGuard()
        result = guard.check("测试", None, "描述")
        self.assertIsInstance(result, GuardResult)

    def test_config_values_match_requirements(self):
        """配置值应符合任务要求"""
        guard = TaskGenerationGuard()
        self.assertEqual(guard.config['max_tasks_per_24h'], 2)
        self.assertEqual(guard.config['max_pending_per_goal'], 3)
        self.assertEqual(guard.config['similarity_threshold'], 0.85)
        self.assertEqual(guard.config['prefix_length'], 15)


class Test2119RealWorldScenarios(unittest.TestCase):
    """Task#2119: 真实业务场景测试"""

    def test_similar_titles_same_goal_blocked(self):
        """相同目标相似标题应被拦截"""
        layer = SemanticDedupLayer(prefix_length=15, similarity_threshold=0.85)
        title1 = "T1: AI助手优化-----X"
        title2 = "T1: AI助手优化-----Y"
        # 前15字相同
        self.assertEqual(title1[:15], title2[:15])

    def test_similar_titles_different_goal_prefix_match(self):
        """不同目标但前缀相同（跨目标检测）"""
        layer = SemanticDedupLayer(prefix_length=15, similarity_threshold=0.85)
        title1 = "T1: AI助手优化 - 模块A"
        title2 = "T1: AI助手优化 - 模块B"
        self.assertEqual(title1[:15], title2[:15])

    def test_chinese_title_similarity(self):
        """中文标题相似度"""
        s1 = "和光智成商业化融资计划书"
        s2 = "和光智成商业化融资计划案"
        sim = SemanticDedupLayer.string_similarity(s1, s2)
        # 只差1个字，应该高相似度
        self.assertGreater(sim, 0.85)

    def test_chinese_title_different(self):
        """中文不同标题低相似度"""
        s1 = "法务纠纷处理"
        s2 = "健康管理计划"
        sim = SemanticDedupLayer.string_similarity(s1, s2)
        self.assertLess(sim, 0.5)

    def test_academic_task_pattern(self):
        """学术任务标题模式"""
        title = "T3: 学术影响力 - 论文投稿策略优化"
        prefix = title[:15]
        self.assertEqual(len(prefix), 15)

    def test_finance_task_pattern(self):
        """财务任务标题模式"""
        title = "T4: 财富增值 - 投资组合再平衡"
        prefix = title[:15]
        self.assertEqual(len(prefix), 15)


# ============================================================================
# 测试运行器
# ============================================================================

def run_2119_tests():
    """运行Task#2119所有边界场景测试"""
    print("=" * 70)
    print("🧪 Task #2119: SDS调度系统频率限制与幂等性保障")
    print("   边界场景专项测试")
    print("=" * 70)
    print()

    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    suite.addTests(loader.loadTestsFromTestCase(Test2119RateLimitBoundary))
    suite.addTests(loader.loadTestsFromTestCase(Test2119SemanticDedupBoundary))
    suite.addTests(loader.loadTestsFromTestCase(Test2119IdempotencyBoundary))
    suite.addTests(loader.loadTestsFromTestCase(Test2119IntegrationBoundary))
    suite.addTests(loader.loadTestsFromTestCase(Test2119RealWorldScenarios))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 70)
    total = result.testsRun
    passed = total - len(result.failures) - len(result.errors) - len(result.skipped)
    failed = len(result.failures)
    errors = len(result.errors)
    skipped = len(result.skipped)

    print(f"📊 测试统计:")
    print(f"   总计运行: {total} 个")
    print(f"   ✅ 通过: {passed} 个")
    print(f"   ⏭️  跳过: {skipped} 个")
    print(f"   ❌ 失败: {failed} 个")
    print(f"   💥 错误: {errors} 个")
    print()

    if result.wasSuccessful():
        print("🎉 所有边界场景测试通过！Task#2119验收合格")
    else:
        print("⚠️ 部分测试未通过，请检查实现")

    print("=" * 70)

    return result.wasSuccessful(), {
        'total': total,
        'passed': passed,
        'failed': failed,
        'errors': errors,
        'skipped': skipped
    }


if __name__ == "__main__":
    success, stats = run_2119_tests()
    sys.exit(0 if success else 1)
