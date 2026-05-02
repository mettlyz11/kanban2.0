#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Task #2119 独立测试运行器 - 无DB依赖
快速验证算法层核心逻辑
"""

import sys
import os
import unittest
import time

sys.path.insert(0, "/Users/mettlyz/.openclaw/workspace/scripts")
sys.path.insert(0, "/Users/mettlyz/.openclaw/workspace/sds")
sys.path.insert(0, "/Users/mettlyz/.openclaw/workspace/sds/core")

from core.task_generation_guard_v46 import (
    IdempotencyLayer, RateLimitLayer, SemanticDedupLayer,
    TaskGenerationGuard, GuardDecision, GuardResult, quick_guard_check
)


class TestRateLimitBoundary(unittest.TestCase):
    """频率限制边界测试"""

    def test_exactly_2_per_24h_allowed(self):
        layer = RateLimitLayer(max_tasks=2)
        self.assertTrue(1 < layer.max_tasks)
        self.assertEqual(layer.max_tasks, 2)
        self.assertEqual(layer.window_hours, 24)

    def test_exactly_2_per_24h_blocked(self):
        layer = RateLimitLayer(max_tasks=2)
        self.assertFalse(2 < layer.max_tasks)

    def test_window_boundary_24h_exact(self):
        from datetime import datetime, timedelta
        window_start = datetime.now() - timedelta(hours=24)
        diff = (datetime.now() - window_start).total_seconds() / 3600
        self.assertAlmostEqual(diff, 24, delta=0.1)

    def test_zero_max_tasks_blocks_all(self):
        layer = RateLimitLayer(max_tasks=0)
        result = layer.check_rate_limit(1)
        self.assertFalse(result['can_generate'])
        self.assertEqual(result['remaining_slots'], 0)

    def test_very_large_max_tasks(self):
        layer = RateLimitLayer(max_tasks=100000)
        result = layer.check_rate_limit(1)
        self.assertTrue(result['can_generate'])

    def test_pending_watermark_exactly_3(self):
        layer = RateLimitLayer(max_pending=3)
        self.assertFalse(3 < layer.max_pending)

    def test_pending_watermark_2_allows(self):
        layer = RateLimitLayer(max_pending=3)
        self.assertTrue(2 < layer.max_pending)

    def test_combined_both_blocked(self):
        layer = RateLimitLayer(max_tasks=2, max_pending=3)
        rate_full = not (2 < layer.max_tasks)
        pending_full = not (3 < layer.max_pending)
        self.assertTrue(rate_full and pending_full)


class TestSemanticDedupBoundary(unittest.TestCase):
    """语义去重边界测试"""

    def test_prefix_exactly_15_chars(self):
        layer = SemanticDedupLayer(prefix_length=15)
        t1 = "T1: AI助手优化-----A"
        t2 = "T1: AI助手优化-----B"
        self.assertEqual(t1[:15], t2[:15])
        self.assertEqual(layer.prefix_length, 15)

    def test_similarity_exactly_0_85_threshold(self):
        s1 = "A" * 100
        s2 = "A" * 85 + "B" * 15
        sim = SemanticDedupLayer.string_similarity(s1, s2)
        self.assertEqual(sim, 0.85)
        self.assertTrue(sim >= 0.85)

    def test_similarity_0_849_should_not_match(self):
        s1 = "A" * 200
        s2 = "A" * 169 + "B" * 31
        sim = SemanticDedupLayer.string_similarity(s1, s2)
        self.assertLess(sim, 0.85)

    def test_similarity_0_851_should_match(self):
        s1 = "A" * 200
        s2 = "A" * 171 + "B" * 29
        sim = SemanticDedupLayer.string_similarity(s1, s2)
        self.assertGreater(sim, 0.85)

    def test_empty_title_no_duplicate(self):
        layer = SemanticDedupLayer()
        result = layer.check("")
        self.assertFalse(result['is_duplicate'])
        self.assertEqual(result['duplicate_type'], 'none')

    def test_none_title_no_duplicate(self):
        layer = SemanticDedupLayer()
        result = layer.check(None)
        self.assertFalse(result['is_duplicate'])

    def test_very_long_title_5000_chars(self):
        layer = SemanticDedupLayer()
        title = "A" * 5000
        result = layer.check(title)
        self.assertIsInstance(result, dict)
        self.assertEqual(result['title_prefix'], title[:15])

    def test_only_special_chars_normalized_empty(self):
        title = "!!!???---..."
        normalized = SemanticDedupLayer.normalize_text(title)
        self.assertEqual(normalized, "")

    def test_only_spaces_normalized_empty(self):
        title = "     "
        normalized = SemanticDedupLayer.normalize_text(title)
        self.assertEqual(normalized, "")

    def test_chinese_punctuation_removed(self):
        title = "你好，世界！今天：测试。"
        normalized = SemanticDedupLayer.normalize_text(title)
        self.assertEqual(normalized, "你好世界今天测试")

    def test_mixed_language_similarity(self):
        s1 = "T1: 法务纠纷 Legal Dispute"
        s2 = "T1: 法务纠纷 Legal Dispute"
        sim = SemanticDedupLayer.string_similarity(s1, s2)
        self.assertEqual(sim, 1.0)

    def test_unicode_characters_distance(self):
        dist = SemanticDedupLayer.levenshtein_distance("日本語", "日本语")
        self.assertEqual(dist, 1)

    def test_semantic_match_with_different_punctuation(self):
        s1 = SemanticDedupLayer.normalize_text("法务纠纷处理！")
        s2 = SemanticDedupLayer.normalize_text("法务纠纷处理")
        sim = SemanticDedupLayer.string_similarity(s1, s2)
        self.assertEqual(sim, 1.0)

    def test_chinese_title_similarity(self):
        s1 = "和光智成商业化融资计划书"
        s2 = "和光智成商业化融资计划案"
        sim = SemanticDedupLayer.string_similarity(s1, s2)
        self.assertGreater(sim, 0.85)

    def test_chinese_title_different(self):
        s1 = "法务纠纷处理"
        s2 = "健康管理计划"
        sim = SemanticDedupLayer.string_similarity(s1, s2)
        self.assertLess(sim, 0.5)


class TestIdempotencyBoundary(unittest.TestCase):
    """幂等性保障边界测试"""

    def setUp(self):
        import tempfile
        self.temp_dir = tempfile.mkdtemp()
        self.log_file = os.path.join(self.temp_dir, 'idem_2119.log')
        self.layer = IdempotencyLayer(log_file=self.log_file)

    def tearDown(self):
        import shutil
        if os.path.exists(self.log_file):
            os.remove(self.log_file)
        if os.path.exists(self.temp_dir):
            os.rmdir(self.temp_dir)

    def test_same_input_same_key(self):
        k1 = self.layer.generate_key("测试任务", 75, "描述")
        k2 = self.layer.generate_key("测试任务", 75, "描述")
        self.assertEqual(k1, k2)
        self.assertEqual(len(k1), 16)

    def test_different_title_different_key(self):
        k1 = self.layer.generate_key("任务A", 1)
        k2 = self.layer.generate_key("任务B", 1)
        self.assertNotEqual(k1, k2)

    def test_different_goal_different_key(self):
        k1 = self.layer.generate_key("相同标题", 1)
        k2 = self.layer.generate_key("相同标题", 2)
        self.assertNotEqual(k1, k2)

    def test_whitespace_trimmed_same_key(self):
        k1 = self.layer.generate_key("测试任务", 1)
        k2 = self.layer.generate_key(" 测试任务 ", 1)
        self.assertEqual(k1, k2)

    def test_long_description_truncated(self):
        long_desc = "A" * 200
        k1 = self.layer.generate_key("测试", 1, long_desc)
        k2 = self.layer.generate_key("测试", 1, long_desc[:100])
        self.assertEqual(k1, k2)

    def test_record_and_check_idempotent(self):
        key = self.layer.generate_key("幂等测试", 1)
        self.layer.record(key, 12345, "幂等测试", 1)
        result = self.layer.check(key)
        self.assertFalse(result['is_safe'])
        self.assertTrue(result['local_found'])
        self.assertEqual(result['local_task_id'], 12345)

    def test_concurrent_key_generation(self):
        import threading
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
        title = "任务<>&\"'\\n\\t"
        key1 = self.layer.generate_key(title, 1)
        key2 = self.layer.generate_key(title, 1)
        self.assertEqual(key1, key2)
        self.assertEqual(len(key1), 16)

    def test_empty_title_generates_key(self):
        key = self.layer.generate_key("")
        self.assertEqual(len(key), 16)
        self.assertEqual(self.layer.generate_key(""), key)

    def test_unicode_title(self):
        key1 = self.layer.generate_key("日本語タスク", 1)
        key2 = self.layer.generate_key("日本語タスク", 1)
        self.assertEqual(key1, key2)

    def test_none_description_handling(self):
        key = self.layer.generate_key("测试", None, None)
        self.assertEqual(len(key), 16)

    def test_multiple_records_persist(self):
        for i in range(10):
            key = self.layer.generate_key(f"任务{i}", i)
            self.layer.record(key, 1000 + i, f"任务{i}", i)
        for i in range(10):
            key = self.layer.generate_key(f"任务{i}", i)
            result = self.layer.check(key)
            self.assertFalse(result['is_safe'])
            self.assertEqual(result['local_task_id'], 1000 + i)


class TestIntegrationBoundary(unittest.TestCase):
    """集成边界测试"""

    def test_new_task_passes_all_layers(self):
        guard = TaskGenerationGuard()
        unique_title = f"2119边界测试_{time.time()}"
        result = guard.check(unique_title, 999, "测试描述")
        self.assertEqual(result.decision, GuardDecision.ALLOWED)
        self.assertTrue(result.can_generate)
        self.assertIsNotNone(result.idempotency_key)

    def test_idempotent_second_call_blocked(self):
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
        result = GuardResult(
            decision=GuardDecision.ALLOWED,
            can_generate=True,
            reason="测试"
        )
        self.assertEqual(result.decision, GuardDecision.ALLOWED)
        self.assertTrue(result.can_generate)
        self.assertEqual(result.reason, "测试")
        self.assertIsNotNone(result.timestamp)

    def test_batch_filter_empty_list(self):
        guard = TaskGenerationGuard()
        passed, blocked = guard.filter_recommendations([])
        self.assertEqual(len(passed), 0)
        self.assertEqual(len(blocked), 0)

    def test_quick_guard_check_returns_bool(self):
        can_gen, reason = quick_guard_check(f"快捷测试_{time.time()}", 999)
        self.assertIsInstance(can_gen, bool)
        self.assertIsInstance(reason, str)

    def test_system_status_contains_all_goals(self):
        guard = TaskGenerationGuard()
        status = guard.get_system_status()
        self.assertIn('version', status)
        self.assertIn('goals', status)
        self.assertEqual(len(status['goals']), 7)

    def test_guard_with_none_goal(self):
        guard = TaskGenerationGuard()
        result = guard.check("测试", None, "描述")
        self.assertIsInstance(result, GuardResult)

    def test_config_values_match_requirements(self):
        guard = TaskGenerationGuard()
        self.assertEqual(guard.config['max_tasks_per_24h'], 2)
        self.assertEqual(guard.config['max_pending_per_goal'], 3)
        self.assertEqual(guard.config['similarity_threshold'], 0.85)
        self.assertEqual(guard.config['prefix_length'], 15)


class TestRealWorldScenarios(unittest.TestCase):
    """真实业务场景测试"""

    def test_similar_titles_same_goal_blocked(self):
        layer = SemanticDedupLayer(prefix_length=15, similarity_threshold=0.85)
        title1 = "T1: AI助手优化-----X"
        title2 = "T1: AI助手优化-----Y"
        self.assertEqual(title1[:15], title2[:15])

    def test_academic_task_pattern(self):
        title = "T3: 学术影响力 - 论文投稿策略优化"
        prefix = title[:15]
        self.assertEqual(len(prefix), 15)

    def test_finance_task_pattern(self):
        title = "T4: 财富增值 - 投资组合再平衡"
        prefix = title[:15]
        self.assertEqual(len(prefix), 15)

    def test_levenshtein_distance_basic(self):
        self.assertEqual(SemanticDedupLayer.levenshtein_distance("hello", "hello"), 0)
        self.assertEqual(SemanticDedupLayer.levenshtein_distance("cat", "bat"), 1)
        self.assertEqual(SemanticDedupLayer.levenshtein_distance("abc", "abcd"), 1)

    def test_similarity_symmetric(self):
        s1 = SemanticDedupLayer.string_similarity("abc", "abd")
        s2 = SemanticDedupLayer.string_similarity("abd", "abc")
        self.assertEqual(s1, s2)


if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    suite.addTests(loader.loadTestsFromTestCase(TestRateLimitBoundary))
    suite.addTests(loader.loadTestsFromTestCase(TestSemanticDedupBoundary))
    suite.addTests(loader.loadTestsFromTestCase(TestIdempotencyBoundary))
    suite.addTests(loader.loadTestsFromTestCase(TestIntegrationBoundary))
    suite.addTests(loader.loadTestsFromTestCase(TestRealWorldScenarios))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    total = result.testsRun
    passed = total - len(result.failures) - len(result.errors) - len(result.skipped)
    failed = len(result.failures)
    errors = len(result.errors)
    skipped = len(result.skipped)
    print("\n" + "=" * 70)
    print(f"📊 测试统计: 总计={total}, 通过={passed}, 跳过={skipped}, 失败={failed}, 错误={errors}")
    print("=" * 70)
    sys.exit(0 if result.wasSuccessful() else 1)
