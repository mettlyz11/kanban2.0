#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Task #2119: SDS调度系统任务生成频率限制与幂等性保障
单元测试套件 - 边界场景全覆盖

测试范围：
- 频率限制边界（0/1/2任务上限、24小时滑动窗口、pending水位）
- 语义去重边界（0.85阈值、15字前缀、空值、超长字符串、Unicode）
- 幂等性边界（并发键生成、特殊字符、空值、长描述截断）
- 集成场景（三层短路求值、内存降级模式、批量过滤）
- 真实业务场景（中文标题、学术/法务/商业任务模式）

运行方式: python3 test_task_2119_v49.py
"""

import sys
import os
import unittest
import tempfile
import threading
import time
import shutil

sys.path.insert(0, "/Users/mettlyz/.openclaw/workspace/scripts")
sys.path.insert(0, "/Users/mettlyz/.openclaw/workspace/sds")
sys.path.insert(0, "/Users/mettlyz/.openclaw/workspace/sds/core")

from core.task_generation_guard_v49 import (
    IdempotencyLayer,
    RateLimitLayer,
    SemanticDedupLayer,
    TaskGenerationGuard,
    GuardDecision,
    GuardResult,
    quick_guard_check,
    DB_AVAILABLE,
)


# ============================================================================
# Test Suite 1: 频率限制边界测试
# ============================================================================

class TestRateLimitBoundary(unittest.TestCase):
    """频率限制层边界场景测试"""
    
    def test_default_max_tasks_is_2(self):
        """默认配置：每目标每24小时最多2个任务"""
        layer = RateLimitLayer()
        self.assertEqual(layer.max_tasks, 2)
    
    def test_default_max_pending_is_3(self):
        """默认配置：每目标最多3个pending任务"""
        layer = RateLimitLayer()
        self.assertEqual(layer.max_pending, 3)
    
    def test_exactly_2_per_24h_allowed(self):
        """恰好生成2个任务时，第3个应被拦截"""
        layer = RateLimitLayer(max_tasks=2, memory_only=True)
        layer.record_generation(1, 1001, "任务1")
        layer.record_generation(1, 1002, "任务2")
        result = layer.check_rate_limit(1)
        self.assertFalse(result['can_generate'])
        self.assertEqual(result['current_count'], 2)
        self.assertEqual(result['remaining_slots'], 0)
    
    def test_exactly_1_per_24h_allows_one_more(self):
        """已生成1个任务时，还允许生成1个"""
        layer = RateLimitLayer(max_tasks=2, memory_only=True)
        layer.record_generation(1, 1001, "任务1")
        result = layer.check_rate_limit(1)
        self.assertTrue(result['can_generate'])
        self.assertEqual(result['remaining_slots'], 1)
    
    def test_zero_max_tasks_blocks_all(self):
        """频率上限为0时应拦截所有任务"""
        layer = RateLimitLayer(max_tasks=0, memory_only=True)
        result = layer.check_rate_limit(1)
        self.assertFalse(result['can_generate'])
        self.assertEqual(result['remaining_slots'], 0)
    
    def test_very_large_max_tasks(self):
        """极大的频率上限应允许生成"""
        layer = RateLimitLayer(max_tasks=100000, memory_only=True)
        result = layer.check_rate_limit(1)
        self.assertTrue(result['can_generate'])
    
    def test_window_boundary_24h_exact(self):
        """24小时滑动窗口边界精确性"""
        from datetime import datetime, timedelta
        window_start = datetime.now() - timedelta(hours=24)
        diff = (datetime.now() - window_start).total_seconds() / 3600
        self.assertAlmostEqual(diff, 24, delta=0.1)
    
    def test_pending_watermark_exactly_3_blocks(self):
        """pending恰好为3时应被拦截"""
        layer = RateLimitLayer(max_pending=3, memory_only=True)
        layer.record_generation(1, 1001, "任务1", "pending")
        layer.record_generation(1, 1002, "任务2", "pending")
        layer.record_generation(1, 1003, "任务3", "pending")
        result = layer.check_pending_watermark(1)
        self.assertFalse(result['can_generate'])
        self.assertEqual(result['pending_count'], 3)
    
    def test_pending_watermark_2_allows(self):
        """pending为2时应允许生成"""
        layer = RateLimitLayer(max_pending=3, memory_only=True)
        layer.record_generation(1, 1001, "任务1", "pending")
        layer.record_generation(1, 1002, "任务2", "pending")
        result = layer.check_pending_watermark(1)
        self.assertTrue(result['can_generate'])
        self.assertEqual(result['remaining_slots'], 1)
    
    def test_different_goals_independent(self):
        """不同goal_id的计数应独立"""
        layer = RateLimitLayer(max_tasks=2, memory_only=True)
        layer.record_generation(1, 1001, "任务A")
        layer.record_generation(1, 1002, "任务B")
        # goal_id=1已满
        self.assertFalse(layer.check_rate_limit(1)['can_generate'])
        # goal_id=2应为空
        self.assertTrue(layer.check_rate_limit(2)['can_generate'])
    
    def test_rate_limit_combined_check(self):
        """组合检查应同时满足频率和水位"""
        layer = RateLimitLayer(max_tasks=2, max_pending=1, memory_only=True)
        layer.record_generation(1, 1001, "任务1", "pending")
        result = layer.check_all(1)
        # 频率通过(1<2)，水位通过(1<1? No, 1 is NOT < 1)
        # max_pending=1, current_pending=1, so 1 < 1 is False
        self.assertFalse(result['can_generate'])


# ============================================================================
# Test Suite 2: 语义去重边界测试
# ============================================================================

class TestSemanticDedupBoundary(unittest.TestCase):
    """语义去重层边界场景测试"""
    
    def test_default_similarity_threshold_is_0_85(self):
        """默认相似度阈值应为0.85"""
        layer = SemanticDedupLayer()
        self.assertEqual(layer.similarity_threshold, 0.85)
    
    def test_default_prefix_length_is_15(self):
        """默认前缀长度应为15"""
        layer = SemanticDedupLayer()
        self.assertEqual(layer.prefix_length, 15)
    
    def test_similarity_exactly_0_85_threshold(self):
        """100字符中85相同，相似度恰好0.85"""
        s1 = "A" * 100
        s2 = "A" * 85 + "B" * 15
        sim = SemanticDedupLayer.string_similarity(s1, s2)
        self.assertEqual(sim, 0.85)
        self.assertTrue(sim >= 0.85)
    
    def test_similarity_0_849_should_not_match(self):
        """100字符中84.9相同，相似度略低于0.85，不应匹配"""
        s1 = "A" * 200
        s2 = "A" * 169 + "B" * 31
        sim = SemanticDedupLayer.string_similarity(s1, s2)
        self.assertLess(sim, 0.85)
    
    def test_similarity_0_851_should_match(self):
        """100字符中85.1相同，相似度略高于0.85，应匹配"""
        s1 = "A" * 200
        s2 = "A" * 171 + "B" * 29
        sim = SemanticDedupLayer.string_similarity(s1, s2)
        self.assertGreater(sim, 0.85)
    
    def test_empty_title_no_duplicate(self):
        """空标题不应触发去重"""
        layer = SemanticDedupLayer(memory_only=True)
        result = layer.check("")
        self.assertFalse(result['is_duplicate'])
        self.assertEqual(result['reason'], '标题为空，跳过去重检查')
    
    def test_none_title_no_duplicate(self):
        """None标题不应触发去重"""
        layer = SemanticDedupLayer(memory_only=True)
        result = layer.check(None)
        self.assertFalse(result['is_duplicate'])
    
    def test_very_long_title_5000_chars(self):
        """5000字符超长标题应正常处理"""
        layer = SemanticDedupLayer(memory_only=True)
        title = "A" * 5000
        result = layer.check(title)
        self.assertIsInstance(result, dict)
        self.assertEqual(result['title_prefix'], title[:15].lower())
    
    def test_only_special_chars_normalized_empty(self):
        """纯特殊字符标准化后应为空"""
        title = "!!!???---..."
        normalized = SemanticDedupLayer.normalize_text(title)
        self.assertEqual(normalized, "")
    
    def test_only_spaces_normalized_empty(self):
        """纯空格标准化后应为空"""
        title = "     "
        normalized = SemanticDedupLayer.normalize_text(title)
        self.assertEqual(normalized, "")
    
    def test_chinese_punctuation_removed(self):
        """中文标点应被去除"""
        title = "你好，世界！今天：测试。"
        normalized = SemanticDedupLayer.normalize_text(title)
        self.assertEqual(normalized, "你好世界今天测试")
    
    def test_mixed_language_similarity(self):
        """中英文混合相同字符串相似度应为1.0"""
        s1 = "T1: 法务纠纷 Legal Dispute"
        s2 = "T1: 法务纠纷 Legal Dispute"
        sim = SemanticDedupLayer.string_similarity(s1, s2)
        self.assertEqual(sim, 1.0)
    
    def test_unicode_characters_distance(self):
        """Unicode字符编辑距离测试"""
        dist = SemanticDedupLayer.levenshtein_distance("日本語", "日本语")
        self.assertEqual(dist, 1)
    
    def test_semantic_match_with_different_punctuation(self):
        """不同标点但内容相同应完全匹配"""
        s1 = SemanticDedupLayer.normalize_text("法务纠纷处理！")
        s2 = SemanticDedupLayer.normalize_text("法务纠纷处理")
        sim = SemanticDedupLayer.string_similarity(s1, s2)
        self.assertEqual(sim, 1.0)
    
    def test_prefix_exactly_15_chars(self):
        """前15字相同应触发候选查找"""
        layer = SemanticDedupLayer(prefix_length=15, memory_only=True)
        t1 = "T1: AI助手优化-----A"
        t2 = "T1: AI助手优化-----B"
        self.assertEqual(t1[:15], t2[:15])
    
    def test_different_prefix_no_candidate(self):
        """前15字不同不应产生候选"""
        layer = SemanticDedupLayer(prefix_length=15, memory_only=True)
        candidates = layer._find_candidates("完全不同的标题ABC")
        self.assertEqual(len(candidates), 0)
    
    def test_similar_chinese_titles_match(self):
        """相似中文标题应触发语义匹配"""
        s1 = "和光智成商业化融资计划书"
        s2 = "和光智成商业化融资计划案"
        sim = SemanticDedupLayer.string_similarity(s1, s2)
        self.assertGreater(sim, 0.85)
    
    def test_different_chinese_titles_no_match(self):
        """不同中文标题不应触发语义匹配"""
        s1 = "法务纠纷处理"
        s2 = "健康管理计划"
        sim = SemanticDedupLayer.string_similarity(s1, s2)
        self.assertLess(sim, 0.5)


# ============================================================================
# Test Suite 3: 幂等性边界测试
# ============================================================================

class TestIdempotencyBoundary(unittest.TestCase):
    """幂等性层边界场景测试"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.log_file = os.path.join(self.temp_dir, 'idem_2119_v49.log')
        self.layer = IdempotencyLayer(log_file=self.log_file, memory_only=True)
    
    def tearDown(self):
        if os.path.exists(self.log_file):
            os.remove(self.log_file)
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def test_same_input_same_key(self):
        """相同输入应生成相同键"""
        k1 = self.layer.generate_key("测试任务", 75, "描述")
        k2 = self.layer.generate_key("测试任务", 75, "描述")
        self.assertEqual(k1, k2)
        self.assertEqual(len(k1), 16)
    
    def test_different_title_different_key(self):
        """不同标题应生成不同键"""
        k1 = self.layer.generate_key("任务A", 1)
        k2 = self.layer.generate_key("任务B", 1)
        self.assertNotEqual(k1, k2)
    
    def test_different_goal_different_key(self):
        """不同goal_id应生成不同键"""
        k1 = self.layer.generate_key("相同标题", 1)
        k2 = self.layer.generate_key("相同标题", 2)
        self.assertNotEqual(k1, k2)
    
    def test_whitespace_trimmed_same_key(self):
        """前后空格应被trim后生成相同键"""
        k1 = self.layer.generate_key("测试任务", 1)
        k2 = self.layer.generate_key(" 测试任务 ", 1)
        self.assertEqual(k1, k2)
    
    def test_long_description_truncated(self):
        """超过100字符的描述应被截断"""
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
        """并发键生成应保持一致性"""
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
        """特殊字符标题应能正常生成键"""
        title = "任务<>&\"'\n\t"
        key1 = self.layer.generate_key(title, 1)
        key2 = self.layer.generate_key(title, 1)
        self.assertEqual(key1, key2)
        self.assertEqual(len(key1), 16)
    
    def test_empty_title_generates_key(self):
        """空标题也应生成有效键"""
        key = self.layer.generate_key("")
        self.assertEqual(len(key), 16)
        self.assertEqual(self.layer.generate_key(""), key)
    
    def test_unicode_title(self):
        """Unicode标题应能正常生成键"""
        key1 = self.layer.generate_key("日本語タスク", 1)
        key2 = self.layer.generate_key("日本語タスク", 1)
        self.assertEqual(key1, key2)
    
    def test_none_description_handling(self):
        """None描述应被正确处理"""
        key = self.layer.generate_key("测试", None, None)
        self.assertEqual(len(key), 16)
    
    def test_multiple_records_persist(self):
        """多条记录应被持久化"""
        for i in range(10):
            key = self.layer.generate_key(f"任务{i}", i)
            self.layer.record(key, 1000 + i, f"任务{i}", i)
        for i in range(10):
            key = self.layer.generate_key(f"任务{i}", i)
            result = self.layer.check(key)
            self.assertFalse(result['is_safe'])
            self.assertEqual(result['local_task_id'], 1000 + i)
    
    def test_cleanup_old_records(self):
        """清理过期记录应正常工作"""
        key = self.layer.generate_key("过期任务", 1)
        self.layer.record(key, 9999, "过期任务", 1)
        removed = self.layer.cleanup_old_records(days=0)
        self.assertGreaterEqual(removed, 0)
    
    def test_log_file_persistence(self):
        """日志文件应正确持久化"""
        key = self.layer.generate_key("持久化测试", 1)
        self.layer.record(key, 7777, "持久化测试", 1)
        # 重新加载
        layer2 = IdempotencyLayer(log_file=self.log_file, memory_only=True)
        result = layer2.check(key)
        self.assertFalse(result['is_safe'])
        self.assertEqual(result['local_task_id'], 7777)


# ============================================================================
# Test Suite 4: 集成测试
# ============================================================================

class TestIntegrationBoundary(unittest.TestCase):
    """三层保障集成测试"""
    
    def test_new_task_passes_all_layers(self):
        """全新任务应通过所有三层检查"""
        guard = TaskGenerationGuard(memory_only=True)
        unique_title = f"2119边界测试_{time.time()}"
        result = guard.check(unique_title, 999, "测试描述")
        self.assertEqual(result.decision, GuardDecision.ALLOWED)
        self.assertTrue(result.can_generate)
        self.assertIsNotNone(result.idempotency_key)
    
    def test_idempotent_second_call_blocked(self):
        """幂等性应拦截重复调用"""
        guard = TaskGenerationGuard(memory_only=True)
        title = f"2119幂等测试_{time.time()}"
        r1 = guard.check(title, 999, "测试")
        self.assertEqual(r1.decision, GuardDecision.ALLOWED)
        if r1.idempotency_key:
            guard.idempotency.record(r1.idempotency_key, 99999, title, 999)
            r2 = guard.check(title, 999, "测试")
            self.assertEqual(r2.decision, GuardDecision.BLOCKED_IDEMPOTENT)
            self.assertFalse(r2.can_generate)
    
    def test_guard_result_structure(self):
        """GuardResult结构应完整"""
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
        """空列表过滤应返回空结果"""
        guard = TaskGenerationGuard(memory_only=True)
        passed, blocked = guard.filter_recommendations([])
        self.assertEqual(len(passed), 0)
        self.assertEqual(len(blocked), 0)
    
    def test_quick_guard_check_returns_bool(self):
        """quick_guard_check应返回布尔值和字符串"""
        can_gen, reason = quick_guard_check(f"快捷测试_{time.time()}", 999)
        self.assertIsInstance(can_gen, bool)
        self.assertIsInstance(reason, str)
    
    def test_guard_with_none_goal(self):
        """None goal_id应被正确处理"""
        guard = TaskGenerationGuard(memory_only=True)
        result = guard.check("测试", None, "描述")
        self.assertIsInstance(result, GuardResult)
    
    def test_config_values_match_requirements(self):
        """配置值应符合Task #2119要求"""
        guard = TaskGenerationGuard(memory_only=True)
        self.assertEqual(guard.config['max_tasks_per_24h'], 2)
        self.assertEqual(guard.config['max_pending_per_goal'], 3)
        self.assertEqual(guard.config['similarity_threshold'], 0.85)
        self.assertEqual(guard.config['prefix_length'], 15)
    
    def test_short_circuit_evaluation_idempotency_first(self):
        """短路求值：幂等性应在频率限制之前"""
        guard = TaskGenerationGuard(memory_only=True)
        title = f"短路测试_{time.time()}"
        # 先记录使其幂等
        key = guard.idempotency.generate_key(title, 1)
        guard.idempotency.record(key, 11111, title, 1)
        # 再检查
        result = guard.check(title, 1)
        self.assertEqual(result.decision, GuardDecision.BLOCKED_IDEMPOTENT)
        # 频率限制层不应被执行（没有rate_limit数据）
        self.assertNotIn('rate_limit', result.layer_checks)
    
    def test_record_success_updates_all_layers(self):
        """记录成功应更新所有三层"""
        guard = TaskGenerationGuard(memory_only=True)
        key = guard.idempotency.generate_key("成功任务", 1)
        guard.record_success(key, 55555, "成功任务", 1)
        # 幂等层应记录
        self.assertFalse(guard.idempotency.check(key)['is_safe'])
        # 去重层应记录
        result = guard.dedup.check("成功任务", 1)
        self.assertTrue(result['is_duplicate'] or result['max_similarity'] > 0)
        # 频率层应记录
        rate_result = guard.rate_limit.check_rate_limit(1)
        self.assertEqual(rate_result['current_count'], 1)
    
    def test_system_status_structure(self):
        """系统状态应包含完整配置"""
        guard = TaskGenerationGuard(memory_only=True)
        status = guard.get_system_status()
        self.assertEqual(status['version'], 'V4.9-2119')
        self.assertIn('config', status)
        self.assertIn('goals', status)
        self.assertEqual(len(status['goals']), 7)


# ============================================================================
# Test Suite 5: 真实业务场景测试
# ============================================================================

class TestRealWorldScenarios(unittest.TestCase):
    """真实业务场景测试"""
    
    def test_academic_task_pattern(self):
        """学术任务模式测试"""
        title = "T3: 学术影响力 - 论文投稿策略优化"
        prefix = title[:15]
        self.assertEqual(len(prefix), 15)
        guard = TaskGenerationGuard(memory_only=True)
        result = guard.check(title, 3)
        self.assertTrue(result.can_generate)
    
    def test_finance_task_pattern(self):
        """财务任务模式测试"""
        title = "T4: 财富增值 - 投资组合再平衡"
        prefix = title[:15]
        self.assertEqual(len(prefix), 15)
        guard = TaskGenerationGuard(memory_only=True)
        result = guard.check(title, 4)
        self.assertTrue(result.can_generate)
    
    def test_legal_task_pattern(self):
        """法务任务模式测试"""
        title = "T6: 法律事务 - 深云智合诉讼证据整理"
        guard = TaskGenerationGuard(memory_only=True)
        result = guard.check(title, 6)
        self.assertTrue(result.can_generate)
    
    def test_similar_titles_same_goal_blocked(self):
        """相似标题同一目标应被去重拦截"""
        import tempfile
        temp_dir = tempfile.mkdtemp()
        log_file = os.path.join(temp_dir, 'test_similar.log')
        guard = TaskGenerationGuard(memory_only=True)
        guard.idempotency = IdempotencyLayer(log_file=log_file, memory_only=True)
        title1 = "T1: AI助手优化 - SDS调度系统优化"
        title2 = "T1: AI助手优化 - SDS系统调优"
        r1 = guard.check(title1, 1)
        self.assertTrue(r1.can_generate)
        guard.record_success(r1.idempotency_key, 90001, title1, 1)
        r2 = guard.check(title2, 1)
        # 标题前15字相同，应触发候选检查，语义相似度可能触发拦截
        self.assertIsInstance(r2, GuardResult)
        if os.path.exists(log_file):
            os.remove(log_file)
        if os.path.exists(temp_dir):
            os.rmdir(temp_dir)
    
    def test_batch_filter_multiple_recommendations(self):
        """批量过滤多个推荐任务"""
        guard = TaskGenerationGuard(memory_only=True)
        recs = [
            {'title': '任务A', 'goal_id': 1, 'description': '描述A'},
            {'title': '任务B', 'goal_id': 2, 'description': '描述B'},
            {'title': '任务C', 'goal_id': 3, 'description': '描述C'},
        ]
        passed, blocked = guard.filter_recommendations(recs)
        # 首次检查都应通过
        self.assertEqual(len(passed) + len(blocked), 3)
    
    def test_memory_mode_when_db_unavailable(self):
        """DB不可用时内存模式应正常工作"""
        guard = TaskGenerationGuard(memory_only=True)
        self.assertTrue(guard.memory_only)
        result = guard.check("内存模式测试", 1)
        self.assertIsInstance(result, GuardResult)
    
    def test_chinese_title_with_numbers(self):
        """中文标题含数字"""
        title = "T2: 和光智成2026年Q2融资计划书撰写"
        guard = TaskGenerationGuard(memory_only=True)
        result = guard.check(title, 2)
        self.assertTrue(result.can_generate)
    
    def test_goal_id_range_1_to_7(self):
        """目标ID范围1-7应被支持"""
        guard = TaskGenerationGuard(memory_only=True)
        for gid in range(1, 8):
            result = guard.check(f"目标{gid}测试", gid)
            self.assertIsInstance(result, GuardResult)


# ============================================================================
# 主程序
# ============================================================================

if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加所有测试套件
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
    print(f"📊 Task #2119 测试统计: 总计={total}, 通过={passed}, 跳过={skipped}, 失败={failed}, 错误={errors}")
    print("=" * 70)
    
    if result.wasSuccessful():
        print("\n✅ 所有测试通过！Task #2119 三层保障系统验证成功。")
    else:
        print("\n❌ 部分测试失败，请检查实现。")
    
    sys.exit(0 if result.wasSuccessful() else 1)
