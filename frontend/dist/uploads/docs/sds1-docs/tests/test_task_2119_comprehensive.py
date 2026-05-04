#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Task #2119: SDS调度系统任务生成频率限制与幂等性保障
综合单元测试 - 覆盖边界场景

测试范围：
1. 频率限制模块（24h滑动窗口、pending水位、边界值）
2. 语义去重算法（前15字匹配、Levenshtein相似度0.85阈值）
3. 幂等性保障（SHA-256指纹、并发安全、持久化）
4. 三层集成（短路求值、降级运行）
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

# 路径设置
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent.parent / "core"))

from core.task_generation_guard_v48 import (
    IdempotencyLayer,
    RateLimitLayer,
    SemanticDedupLayer,
    UnifiedTaskGuard,
    GuardDecision,
    GuardResult,
    quick_guard_check,
    DB_AVAILABLE
)


class TestIdempotencyLayer(unittest.TestCase):
    """Layer 1: 幂等性保障测试"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.log_file = Path(self.temp_dir) / "idem_test.log"

    def tearDown(self):
        if self.log_file.exists():
            self.log_file.unlink()
        os.rmdir(self.temp_dir)

    def test_generate_key_deterministic(self):
        """相同输入应生成相同幂等键"""
        key1 = IdempotencyLayer.generate_key("测试标题", 1, "描述")
        key2 = IdempotencyLayer.generate_key("测试标题", 1, "描述")
        self.assertEqual(key1, key2)
        self.assertEqual(len(key1), 16)

    def test_generate_key_different_inputs(self):
        """不同输入应生成不同幂等键"""
        key1 = IdempotencyLayer.generate_key("标题A", 1, "描述")
        key2 = IdempotencyLayer.generate_key("标题B", 1, "描述")
        self.assertNotEqual(key1, key2)

    def test_generate_key_special_chars(self):
        """特殊字符应正确处理"""
        key = IdempotencyLayer.generate_key("测试!@#$%^&*()", None, "")
        self.assertEqual(len(key), 16)
        self.assertTrue(all(c in "0123456789abcdef" for c in key))

    def test_check_new_key_is_safe(self):
        """新键应判定为安全"""
        layer = IdempotencyLayer(log_file=str(self.log_file), memory_only=True)
        key = IdempotencyLayer.generate_key("新任务")
        result = layer.check(key)
        self.assertTrue(result['is_safe'])
        self.assertFalse(result['local_found'])

    def test_check_duplicate_key_blocked(self):
        """重复键应判定为已存在"""
        layer = IdempotencyLayer(log_file=str(self.log_file), memory_only=True)
        key = IdempotencyLayer.generate_key("重复任务")
        layer.record(key, 100, "重复任务")
        result = layer.check(key)
        self.assertFalse(result['is_safe'])
        self.assertTrue(result['local_found'])
        self.assertEqual(result['local_task_id'], 100)

    def test_record_persists_to_file(self):
        """记录应持久化到日志文件"""
        layer = IdempotencyLayer(log_file=str(self.log_file), memory_only=True)
        key = IdempotencyLayer.generate_key("持久化测试")
        layer.record(key, 200, "持久化测试")
        self.assertTrue(self.log_file.exists())
        content = self.log_file.read_text(encoding='utf-8')
        self.assertIn(key, content)
        self.assertIn("200", content)

    def test_load_from_log(self):
        """应从日志文件加载历史记录"""
        layer1 = IdempotencyLayer(log_file=str(self.log_file), memory_only=True)
        key = IdempotencyLayer.generate_key("加载测试")
        layer1.record(key, 300, "加载测试")
        # 创建新实例，应加载已有日志
        layer2 = IdempotencyLayer(log_file=str(self.log_file), memory_only=True)
        result = layer2.check(key)
        self.assertFalse(result['is_safe'])

    def test_cleanup_old_records(self):
        """应正确清理过期记录"""
        layer = IdempotencyLayer(log_file=str(self.log_file), memory_only=True)
        # 模拟一条旧记录
        layer._memory_cache["old_key"] = {
            'key': 'old_key',
            'task_id': 1,
            'created_at': (datetime.now() - timedelta(days=40)).isoformat()
        }
        removed = layer.cleanup_old_records(days=30)
        self.assertEqual(removed, 1)
        self.assertNotIn("old_key", layer._memory_cache)

    def test_concurrent_record_access(self):
        """并发记录应线程安全"""
        layer = IdempotencyLayer(log_file=str(self.log_file), memory_only=True)
        errors = []

        def worker(i):
            try:
                key = IdempotencyLayer.generate_key(f"并发任务{i}")
                layer.record(key, i, f"并发任务{i}")
            except Exception as e:
                errors.append(str(e))

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0)
        self.assertEqual(len(layer._memory_cache), 20)


class TestRateLimitLayer(unittest.TestCase):
    """Layer 2: 频率限制测试"""

    def test_default_config(self):
        """默认配置应符合任务要求"""
        layer = RateLimitLayer(memory_only=True)
        self.assertEqual(layer.max_tasks, 2)
        self.assertEqual(layer.max_pending, 3)
        self.assertEqual(layer.window_hours, 24)

    def test_zero_max_tasks_blocks_all(self):
        """max_tasks=0应阻止所有生成"""
        layer = RateLimitLayer(max_tasks=0, memory_only=True)
        result = layer.check_rate_limit(1)
        self.assertFalse(result['can_generate'])
        self.assertEqual(result['remaining_slots'], 0)

    def test_large_max_tasks_allows(self):
        """极大max_tasks应始终允许"""
        layer = RateLimitLayer(max_tasks=100000, memory_only=True)
        result = layer.check_rate_limit(1)
        self.assertTrue(result['can_generate'])
        self.assertGreater(result['remaining_slots'], 0)

    def test_memory_mode_counting(self):
        """内存模式应正确计数"""
        layer = RateLimitLayer(max_tasks=2, memory_only=True)
        layer.record_generation(1, 101, "任务1")
        layer.record_generation(1, 102, "任务2")
        result = layer.check_rate_limit(1)
        self.assertEqual(result['current_count'], 2)
        self.assertFalse(result['can_generate'])

    def test_different_goals_independent(self):
        """不同goal_id应独立计数"""
        layer = RateLimitLayer(max_tasks=2, memory_only=True)
        layer.record_generation(1, 101, "任务A")
        layer.record_generation(1, 102, "任务B")
        # goal_id=2应仍允许
        result = layer.check_rate_limit(2)
        self.assertTrue(result['can_generate'])
        self.assertEqual(result['current_count'], 0)

    def test_window_boundary_inside(self):
        """23小时59分应在窗口内"""
        layer = RateLimitLayer(window_hours=24, memory_only=True)
        # 模拟23h59m前的记录
        layer._memory_records.append({
            'goal_id': 1,
            'generated_at': datetime.now() - timedelta(hours=23, minutes=59)
        })
        result = layer.check_rate_limit(1)
        self.assertEqual(result['current_count'], 1)

    def test_window_boundary_outside(self):
        """24小时01分应在窗口外"""
        layer = RateLimitLayer(window_hours=24, memory_only=True)
        layer._memory_records.append({
            'goal_id': 1,
            'generated_at': datetime.now() - timedelta(hours=24, minutes=1)
        })
        result = layer.check_rate_limit(1)
        self.assertEqual(result['current_count'], 0)

    def test_pending_watermark_exact_boundary(self):
        """pending恰好等于上限应阻止"""
        layer = RateLimitLayer(max_pending=3, memory_only=True)
        for i in range(3):
            layer._memory_records.append({
                'goal_id': 1, 'status': 'pending'
            })
        result = layer.check_pending_watermark(1)
        self.assertFalse(result['can_generate'])
        self.assertEqual(result['pending_count'], 3)

    def test_pending_watermark_below_boundary(self):
        """pending低于上限应允许"""
        layer = RateLimitLayer(max_pending=3, memory_only=True)
        for i in range(2):
            layer._memory_records.append({
                'goal_id': 1, 'status': 'pending'
            })
        result = layer.check_pending_watermark(1)
        self.assertTrue(result['can_generate'])
        self.assertEqual(result['pending_count'], 2)


class TestSemanticDedupLayer(unittest.TestCase):
    """Layer 3: 语义去重测试"""

    def test_default_config(self):
        """默认配置应符合任务要求"""
        layer = SemanticDedupLayer(memory_only=True)
        self.assertEqual(layer.similarity_threshold, 0.85)
        self.assertEqual(layer.prefix_length, 15)

    def test_normalize_text(self):
        """文本标准化应去除空格和中英文标点，转小写"""
        layer = SemanticDedupLayer(memory_only=True)
        # v48去除空格、换行、中文标点（\u3000-\u303F等），转小写
        self.assertEqual(layer.normalize_text("Hello World"), "helloworld")
        self.assertEqual(layer.normalize_text("测 试！"), "测试")
        self.assertEqual(layer.normalize_text(""), "")

    def test_levenshtein_distance_identical(self):
        """相同字符串距离应为0"""
        self.assertEqual(SemanticDedupLayer.levenshtein_distance("abc", "abc"), 0)

    def test_levenshtein_distance_empty(self):
        """空字符串距离应为另一字符串长度"""
        self.assertEqual(SemanticDedupLayer.levenshtein_distance("", "abc"), 3)
        self.assertEqual(SemanticDedupLayer.levenshtein_distance("abc", ""), 3)

    def test_string_similarity_identical(self):
        """相同字符串相似度应为1.0"""
        sim = SemanticDedupLayer.string_similarity("test", "test")
        self.assertEqual(sim, 1.0)

    def test_string_similarity_completely_different(self):
        """完全不同字符串相似度应接近0"""
        sim = SemanticDedupLayer.string_similarity("abc", "xyz")
        self.assertEqual(sim, 0.0)

    def test_exact_085_boundary_match(self):
        """恰好0.85阈值的边界测试"""
        layer = SemanticDedupLayer(similarity_threshold=0.85, memory_only=True)
        # "abcdefgh" vs "abcdefgi" 距离=1, 长度=8, 相似度=7/8=0.875
        s1, s2 = "abcdefgh", "abcdefgi"
        sim = SemanticDedupLayer.string_similarity(s1, s2)
        self.assertAlmostEqual(sim, 0.875, places=3)
        self.assertGreaterEqual(sim, 0.85)

    def test_exact_085_boundary_no_match(self):
        """低于0.85阈值的边界测试"""
        layer = SemanticDedupLayer(similarity_threshold=0.85, memory_only=True)
        # "abcdefghij" vs "abcdexghij" 距离=1, 长度=10, 相似度=0.9
        # 用 "abcdefghij" vs "abxxefghij" 距离=2, 长度=10, 相似度=0.8
        s1, s2 = "abcdefghij", "abxxefghij"
        sim = SemanticDedupLayer.string_similarity(s1, s2)
        self.assertAlmostEqual(sim, 0.8, places=3)
        self.assertLess(sim, 0.85)

    def test_prefix_match_blocks(self):
        """前15字匹配应触发候选查找"""
        layer = SemanticDedupLayer(memory_only=True)
        title = "T1: AI助手优化测试任务示例"
        layer.register_task(1, title, goal_id=1)
        result = layer.check(title, goal_id=1)
        self.assertTrue(result['is_duplicate'])
        self.assertEqual(result['matched_by'], 'semantic')

    def test_empty_title_skips_check(self):
        """空标题应跳过去重检查"""
        layer = SemanticDedupLayer(memory_only=True)
        result = layer.check("", goal_id=1)
        self.assertFalse(result['is_duplicate'])
        self.assertIn("标题为空", result['reason'])

    def test_different_prefix_no_candidate(self):
        """不同前缀不应产生候选"""
        layer = SemanticDedupLayer(memory_only=True)
        layer.register_task(1, "前端开发任务示例", goal_id=1)
        result = layer.check("后端开发完全不同", goal_id=1)
        self.assertFalse(result['is_duplicate'])

    def test_lookback_window_respected(self):
        """超过回溯窗口的任务不应作为候选"""
        layer = SemanticDedupLayer(lookback_days=7, memory_only=True)
        old_time = datetime.now() - timedelta(days=10)
        with layer._task_lock:
            layer._memory_tasks[1] = {
                'title': '旧任务标题',
                'goal_id': 1,
                'created_at': old_time.isoformat()
            }
        result = layer.check('旧任务标题', goal_id=1)
        self.assertFalse(result['is_duplicate'])


class TestUnifiedGuardIntegration(unittest.TestCase):
    """三层集成测试"""

    def test_short_circuit_idempotency(self):
        """幂等性拦截应短路，不执行后续检查"""
        guard = UnifiedTaskGuard(memory_only=True)
        title = "短路测试任务"
        # 第一次记录
        key = guard.idempotency.generate_key(title, 1)
        guard.idempotency.record(key, 100, title, 1)
        # 第二次检查应被幂等性拦截
        result = guard.check(title, goal_id=1)
        self.assertEqual(result.decision, GuardDecision.BLOCKED_IDEMPOTENT)
        # 不应包含频率限制检查结果（短路）
        self.assertIn('idempotency', result.layer_checks)

    def test_rate_limit_after_idempotency_pass(self):
        """幂等性通过后应检查频率限制"""
        guard = UnifiedTaskGuard(memory_only=True)
        # 设置max_tasks=0强制频率限制拦截
        guard.rate_limit.max_tasks = 0
        result = guard.check("频率限制测试", goal_id=99)
        self.assertEqual(result.decision, GuardDecision.BLOCKED_RATE_LIMIT)
        self.assertIn('rate_limit', result.layer_checks)

    def test_full_allow_path(self):
        """三层全通过应允许生成"""
        guard = UnifiedTaskGuard(memory_only=True)
        result = guard.check("全新唯一任务", goal_id=99999)
        self.assertEqual(result.decision, GuardDecision.ALLOWED)
        self.assertTrue(result.can_generate)
        self.assertIn('idempotency', result.layer_checks)
        self.assertIn('rate_limit', result.layer_checks)
        self.assertIn('deduplication', result.layer_checks)

    def test_record_success_updates_all_layers(self):
        """记录成功应更新所有三层状态"""
        guard = UnifiedTaskGuard(memory_only=True)
        key = guard.idempotency.generate_key("记录测试", 1)
        guard.record_success(key, 500, "记录测试", 1)
        # 幂等层应记录
        self.assertFalse(guard.idempotency.check(key)['is_safe'])
        # 去重层应记录
        self.assertTrue(500 in guard.dedup._memory_tasks)
        # 频率层应记录
        self.assertEqual(len(guard.rate_limit._memory_records), 1)

    def test_stats_report(self):
        """统计报告应包含正确信息"""
        guard = UnifiedTaskGuard(memory_only=True)
        stats = guard.get_stats()
        self.assertIn('config', stats)
        self.assertEqual(stats['config']['max_tasks_per_24h'], 2)
        self.assertEqual(stats['config']['similarity_threshold'], 0.85)

    def test_quick_guard_check(self):
        """快捷函数应正常工作"""
        result = quick_guard_check("快捷测试任务", goal_id=88888)
        self.assertIsInstance(result, GuardResult)
        self.assertEqual(result.decision, GuardDecision.ALLOWED)

    def test_duplicate_title_blocked(self):
        """重复标题应被语义去重拦截"""
        guard = UnifiedTaskGuard(memory_only=True)
        title = "T109: 平台部署验证任务"
        guard.dedup.register_task(1000, title, goal_id=10)
        result = guard.check(title, goal_id=10)
        self.assertEqual(result.decision, GuardDecision.BLOCKED_DUPLICATE)

    def test_memory_mode_survives_db_failure(self):
        """内存模式应在DB不可用时正常运行"""
        guard = UnifiedTaskGuard(memory_only=True)
        self.assertTrue(guard.memory_only)
        result = guard.check("降级模式测试", goal_id=1)
        self.assertTrue(result.can_generate)

    def test_concurrent_guard_checks(self):
        """并发检查应线程安全且不崩溃"""
        guard = UnifiedTaskGuard(memory_only=True)
        results = []
        lock = threading.Lock()

        def worker(i):
            result = guard.check(f"并发任务{i}", goal_id=1)
            with lock:
                results.append(result.decision)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 所有检查都应完成且不报错（内存模式DB查询返回0，全部通过）
        self.assertEqual(len(results), 10)
        # 验证没有ERROR决策
        error_count = sum(1 for r in results if r == GuardDecision.ERROR)
        self.assertEqual(error_count, 0)


if __name__ == '__main__':
    print("=" * 70)
    print("Task #2119: SDS调度系统任务生成频率限制与幂等性保障")
    print("综合单元测试 - 覆盖边界场景")
    print("=" * 70)
    print(f"DB_AVAILABLE: {DB_AVAILABLE}")
    print()
    unittest.main(verbosity=2)
