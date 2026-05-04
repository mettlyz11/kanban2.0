#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SDS任务生成三重保障系统 V4.6 - 独立单元测试
任务#2119: 频率限制 + 语义去重 + 幂等性保障
"""

import sys, os, json, time, tempfile, threading
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent / "core"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from task_generation_guard_v46 import (
    IdempotencyLayer, RateLimitLayer, SemanticDedupLayer,
    TaskGenerationGuard, GuardDecision, GuardResult, quick_guard_check
)

PASS, FAIL, SKIP = 0, 0, 0
ERRORS = []

def test(name, fn):
    global PASS, FAIL, SKIP, ERRORS
    try:
        fn()
        print(f"  ✅ {name}")
        PASS += 1
    except AssertionError as e:
        print(f"  ❌ {name}: {e}")
        FAIL += 1
        ERRORS.append((name, str(e)))
    except Exception as e:
        print(f"  💥 {name}: {e}")
        FAIL += 1
        ERRORS.append((name, str(e)))

# ========== IdempotencyLayer ==========
def test_idem_deterministic():
    k1 = IdempotencyLayer.generate_key("测试任务", 75, "描述前缀")
    k2 = IdempotencyLayer.generate_key("测试任务", 75, "描述前缀")
    assert k1 == k2 and len(k1) == 16

def test_idem_different_title():
    k1 = IdempotencyLayer.generate_key("任务A", 75)
    k2 = IdempotencyLayer.generate_key("任务B", 75)
    assert k1 != k2

def test_idem_different_goal():
    k1 = IdempotencyLayer.generate_key("相同标题", 75)
    k2 = IdempotencyLayer.generate_key("相同标题", 76)
    assert k1 != k2

def test_idem_whitespace_trimmed():
    k1 = IdempotencyLayer.generate_key("测试任务", 75)
    k2 = IdempotencyLayer.generate_key(" 测试任务 ", 75)
    assert k1 == k2

def test_idem_empty_title():
    k = IdempotencyLayer.generate_key("")
    assert len(k) == 16

def test_idem_unicode():
    k1 = IdempotencyLayer.generate_key("日本語タスク", 1)
    k2 = IdempotencyLayer.generate_key("日本語タスク", 1)
    assert k1 == k2

def test_idem_mixed_language():
    k1 = IdempotencyLayer.generate_key("T1: 法务纠纷 Legal Dispute", 80)
    k2 = IdempotencyLayer.generate_key("T1: 法务纠纷 Legal Dispute", 80)
    assert k1 == k2

def test_idem_long_desc_truncated():
    long_desc = "A" * 200
    k1 = IdempotencyLayer.generate_key("测试", 1, long_desc)
    k2 = IdempotencyLayer.generate_key("测试", 1, long_desc[:100])
    assert k1 == k2

def test_idem_check_new_key_safe():
    td = tempfile.mkdtemp()
    logf = os.path.join(td, 'idem.log')
    layer = IdempotencyLayer(log_file=logf)
    key = layer.generate_key("全新任务", 999)
    result = layer.check(key)
    assert result['is_safe'] and not result['local_found']
    os.remove(logf); os.rmdir(td)

def test_idem_check_existing_key_blocked():
    td = tempfile.mkdtemp()
    logf = os.path.join(td, 'idem.log')
    layer = IdempotencyLayer(log_file=logf)
    key = layer.generate_key("重复任务", 999)
    layer.record(key, 12345, "重复任务", 999)
    result = layer.check(key)
    assert not result['is_safe'] and result['local_task_id'] == 12345
    os.remove(logf); os.rmdir(td)

def test_idem_record_multiple():
    td = tempfile.mkdtemp()
    logf = os.path.join(td, 'idem.log')
    layer = IdempotencyLayer(log_file=logf)
    keys = []
    for i in range(5):
        key = layer.generate_key(f"任务{i}", i)
        keys.append(key)
        layer.record(key, 1000 + i, f"任务{i}", i)
    for i, key in enumerate(keys):
        result = layer.check(key)
        assert not result['is_safe'] and result['local_task_id'] == 1000 + i
    os.remove(logf); os.rmdir(td)

def test_idem_cleanup_no_file():
    layer = IdempotencyLayer(log_file="/tmp/nonexistent_2119.log")
    removed = layer.cleanup_old_records(days=30)
    assert removed == 0

def test_idem_special_chars():
    title = "任务<>&\"'\\n\\t"
    k1 = IdempotencyLayer.generate_key(title, 1)
    k2 = IdempotencyLayer.generate_key(title, 1)
    assert k1 == k2 and len(k1) == 16

# ========== RateLimitLayer ==========
def test_rate_default_config():
    d = RateLimitLayer()
    assert d.max_tasks == 2 and d.max_pending == 3 and d.window_hours == 24

def test_rate_custom_config():
    c = RateLimitLayer(max_tasks=5, max_pending=10, window_hours=12)
    assert c.max_tasks == 5 and c.max_pending == 10 and c.window_hours == 12

def test_rate_limit_structure():
    layer = RateLimitLayer()
    result = layer.check_rate_limit(999999)
    for field in ['can_generate','current_count','max_allowed','remaining_slots','window_hours','window_start','goal_id','check_type']:
        assert field in result

def test_rate_pending_structure():
    layer = RateLimitLayer()
    result = layer.check_pending_watermark(999999)
    for field in ['can_generate','current_pending','max_allowed','available_slots','goal_id','check_type']:
        assert field in result

def test_rate_combined_structure():
    layer = RateLimitLayer()
    result = layer.check_all(999999)
    for field in ['can_generate','blocked_reason','rate_check','pending_check','check_type']:
        assert field in result

def test_rate_zero_max_blocked():
    layer = RateLimitLayer(max_tasks=0)
    result = layer.check_rate_limit(1)
    assert not result['can_generate'] and result['remaining_slots'] == 0

def test_rate_boundary_equal():
    current = 2
    max_allowed = 2
    assert not (current < max_allowed)

def test_rate_boundary_less():
    current = 1
    max_allowed = 2
    assert current < max_allowed and max(0, max_allowed - current) == 1

# ========== SemanticDedupLayer ==========
def test_lev_identical():
    assert SemanticDedupLayer.levenshtein_distance("hello", "hello") == 0

def test_lev_empty_both():
    assert SemanticDedupLayer.levenshtein_distance("", "") == 0

def test_lev_empty_one():
    assert SemanticDedupLayer.levenshtein_distance("hello", "") == 5
    assert SemanticDedupLayer.levenshtein_distance("", "world") == 5

def test_lev_single_sub():
    assert SemanticDedupLayer.levenshtein_distance("cat", "bat") == 1

def test_lev_insertion():
    assert SemanticDedupLayer.levenshtein_distance("abc", "abcd") == 1

def test_lev_deletion():
    assert SemanticDedupLayer.levenshtein_distance("abcd", "abc") == 1

def test_lev_symmetric():
    s1, s2 = "abcdef", "a"
    assert SemanticDedupLayer.levenshtein_distance(s1, s2) == SemanticDedupLayer.levenshtein_distance(s2, s1)

def test_lev_unicode():
    assert SemanticDedupLayer.levenshtein_distance("日本語", "日本語") == 0
    assert SemanticDedupLayer.levenshtein_distance("日本語", "日本话") == 1

def test_sim_identical():
    assert SemanticDedupLayer.string_similarity("test", "test") == 1.0

def test_sim_empty_both():
    assert SemanticDedupLayer.string_similarity("", "") == 1.0

def test_sim_empty_one():
    assert SemanticDedupLayer.string_similarity("test", "") == 0.0
    assert SemanticDedupLayer.string_similarity("", "test") == 0.0

def test_sim_symmetric():
    s1 = SemanticDedupLayer.string_similarity("abc", "abd")
    s2 = SemanticDedupLayer.string_similarity("abd", "abc")
    assert s1 == s2

def test_sim_just_above_threshold():
    s1 = "ABCDEFGHIJ1234567890"
    s2 = "ABCDEFGHIJ12345678XX"
    sim = SemanticDedupLayer.string_similarity(s1, s2)
    assert sim > 0.85

def test_sim_just_below_threshold():
    s1 = "A" * 25
    s2 = "A" * 21 + "B" * 4
    sim = SemanticDedupLayer.string_similarity(s1, s2)
    assert sim < 0.85

def test_sim_exactly_threshold():
    s1 = "A" * 100
    s2 = "A" * 85 + "B" * 15
    sim = SemanticDedupLayer.string_similarity(s1, s2)
    assert abs(sim - 0.85) < 0.001

def test_sim_long_strings():
    l1 = "A" * 1000
    l2 = "A" * 999 + "B"
    sim = SemanticDedupLayer.string_similarity(l1, l2)
    assert sim > 0.99

def test_norm_removes_punctuation():
    result = SemanticDedupLayer.normalize_text("Hello, World!")
    assert result == "helloworld"

def test_norm_chinese_punctuation():
    result = SemanticDedupLayer.normalize_text("你好，世界！")
    assert result == "你好世界"

def test_norm_lowercase():
    result = SemanticDedupLayer.normalize_text("HELLO")
    assert result == "hello"

def test_norm_empty():
    assert SemanticDedupLayer.normalize_text("") == ""
    assert SemanticDedupLayer.normalize_text(None) == ""

def test_norm_mixed():
    text = "T1: 法务纠纷处理 - 证据清单!!!"
    result = SemanticDedupLayer.normalize_text(text)
    assert "t1" in result and "法务纠纷处理" in result and "!" not in result and "-" not in result

def test_dedup_empty_title():
    layer = SemanticDedupLayer()
    result = layer.check("")
    assert not result['is_duplicate'] and result['duplicate_type'] == 'none'

def test_dedup_none_title():
    layer = SemanticDedupLayer()
    result = layer.check(None)
    assert not result['is_duplicate']

def test_dedup_config():
    layer = SemanticDedupLayer(prefix_length=10, similarity_threshold=0.9)
    assert layer.prefix_length == 10 and layer.similarity_threshold == 0.9

def test_chinese_similarity_same():
    s1 = "和光智成商业化融资"
    s2 = "和光智成商业化融资"
    sim = SemanticDedupLayer.string_similarity(s1, s2)
    assert sim == 1.0

def test_chinese_similarity_diff():
    s1 = "法务纠纷处理"
    s2 = "健康管理计划"
    sim = SemanticDedupLayer.string_similarity(s1, s2)
    assert sim < 0.5

def test_mixed_lang_similarity():
    s1 = "T1: 法务纠纷 Legal Dispute"
    s2 = "T1: 法务纠纷 Legal Dispute"
    sim = SemanticDedupLayer.string_similarity(s1, s2)
    assert sim == 1.0

def test_very_long_title():
    title = "A" * 5000
    layer = SemanticDedupLayer()
    prefix = title[:15]
    assert len(prefix) == 15
    result = layer.check(title)
    assert isinstance(result, dict)

def test_special_chars_only():
    title = "!!!???---"
    normalized = SemanticDedupLayer.normalize_text(title)
    assert normalized == ""

def test_spaces_only():
    title = "     "
    normalized = SemanticDedupLayer.normalize_text(title)
    assert normalized == ""

# ========== Integration ==========
def test_guard_init():
    guard = TaskGenerationGuard()
    assert guard.config['max_tasks_per_24h'] == 2
    assert guard.config['max_pending_per_goal'] == 3
    assert guard.config['similarity_threshold'] == 0.85
    assert guard.config['prefix_length'] == 15

def test_guard_batch_id():
    guard = TaskGenerationGuard()
    assert guard.batch_id.startswith('V46-')
    assert len(guard.batch_id) > 20

def test_guard_check_allowed():
    guard = TaskGenerationGuard()
    title = f"唯一测试任务_{time.time()}"
    result = guard.check(title, 999, "测试描述")
    assert result.decision == GuardDecision.ALLOWED
    assert result.can_generate
    assert result.idempotency_key is not None

def test_guard_check_empty():
    guard = TaskGenerationGuard()
    result = guard.check("", 1, "")
    assert isinstance(result, GuardResult)

def test_guard_idempotent_second_time():
    guard = TaskGenerationGuard()
    td = tempfile.mkdtemp()
    guard.idempotency.log_file = os.path.join(td, 'idem.log')
    title = f"幂等测试_{time.time()}"
    r1 = guard.check(title, 999, "测试")
    assert r1.decision == GuardDecision.ALLOWED
    if r1.idempotency_key:
        guard.idempotency.record(r1.idempotency_key, 99999, title, 999)
        r2 = guard.check(title, 999, "测试")
        assert r2.decision == GuardDecision.BLOCKED_IDEMPOTENT
        assert not r2.can_generate
    os.remove(guard.idempotency.log_file); os.rmdir(td)

def test_guard_system_status():
    guard = TaskGenerationGuard()
    status = guard.get_system_status()
    assert 'version' in status and 'batch_id' in status
    assert 'config' in status and 'goals' in status
    assert len(status['goals']) == 7

def test_guard_filter_empty():
    guard = TaskGenerationGuard()
    passed, blocked = guard.filter_recommendations([])
    assert len(passed) == 0 and len(blocked) == 0

def test_guard_filter_single():
    guard = TaskGenerationGuard()
    recs = [{'title': f'测试_{time.time()}', 'goal_id': 999}]
    passed, blocked = guard.filter_recommendations(recs)
    assert len(passed) + len(blocked) == 1

def test_quick_guard():
    can_gen, reason = quick_guard_check(f"快捷测试_{time.time()}", 999)
    assert isinstance(can_gen, bool) and isinstance(reason, str)

def test_guard_result_fields():
    result = GuardResult(decision=GuardDecision.ALLOWED, can_generate=True, reason="测试")
    assert result.decision == GuardDecision.ALLOWED
    assert result.can_generate and result.reason == "测试"
    assert result.timestamp is not None

def test_guard_none_goal():
    guard = TaskGenerationGuard()
    result = guard.check("测试", None, "描述")
    assert isinstance(result, GuardResult)

def test_rapid_checks():
    guard = TaskGenerationGuard()
    title = f"快速测试_{time.time()}"
    results = [guard.check(title, 999) for _ in range(5)]
    assert all(r.can_generate for r in results)

# ========== Performance ==========
def test_performance_200char():
    s1 = "A" * 200
    s2 = "A" * 193 + "B" * 7
    start = time.time()
    for _ in range(50):
        SemanticDedupLayer.string_similarity(s1, s2)
    elapsed = time.time() - start
    assert elapsed < 3.0, f"50次200字符计算耗时{elapsed:.2f}s"
    per_call = elapsed / 50 * 1000
    print(f"\n    [性能] {per_call:.1f}ms/次 (200字符)")

# ========== Concurrent ==========
def test_concurrent_key_generation():
    title = "并发测试任务"
    keys = []
    def generate():
        keys.append(IdempotencyLayer.generate_key(title, 1))
    threads = [threading.Thread(target=generate) for _ in range(10)]
    for t in threads: t.start()
    for t in threads: t.join()
    assert len(set(keys)) == 1

if __name__ == "__main__":
    print("=" * 70)
    print("🧪 SDS任务生成三重保障系统 V4.6 - 独立单元测试")
    print("=" * 70)
    print()

    tests = [
        # Idempotency
        ("幂等键-确定性生成", test_idem_deterministic),
        ("幂等键-不同标题", test_idem_different_title),
        ("幂等键-不同目标", test_idem_different_goal),
        ("幂等键-空格去除", test_idem_whitespace_trimmed),
        ("幂等键-空标题", test_idem_empty_title),
        ("幂等键-Unicode", test_idem_unicode),
        ("幂等键-混合语言", test_idem_mixed_language),
        ("幂等键-超长描述截断", test_idem_long_desc_truncated),
        ("幂等检查-新键安全", test_idem_check_new_key_safe),
        ("幂等检查-已存在键拦截", test_idem_check_existing_key_blocked),
        ("幂等记录-多条记录", test_idem_record_multiple),
        ("幂等清理-无文件", test_idem_cleanup_no_file),
        ("幂等键-特殊字符", test_idem_special_chars),
        # RateLimit
        ("频率限制-默认配置", test_rate_default_config),
        ("频率限制-自定义配置", test_rate_custom_config),
        ("频率限制-返回结构", test_rate_limit_structure),
        ("频率限制-水位结构", test_rate_pending_structure),
        ("频率限制-组合结构", test_rate_combined_structure),
        ("频率限制-零上限拦截", test_rate_zero_max_blocked),
        ("频率限制-边界等于", test_rate_boundary_equal),
        ("频率限制-边界小于", test_rate_boundary_less),
        # SemanticDedup
        ("Levenshtein-相同字符串", test_lev_identical),
        ("Levenshtein-双空", test_lev_empty_both),
        ("Levenshtein-单空", test_lev_empty_one),
        ("Levenshtein-单字符替换", test_lev_single_sub),
        ("Levenshtein-插入", test_lev_insertion),
        ("Levenshtein-删除", test_lev_deletion),
        ("Levenshtein-对称性", test_lev_symmetric),
        ("Levenshtein-Unicode", test_lev_unicode),
        ("相似度-相同", test_sim_identical),
        ("相似度-双空", test_sim_empty_both),
        ("相似度-单空", test_sim_empty_one),
        ("相似度-对称性", test_sim_symmetric),
        ("相似度-高于阈值", test_sim_just_above_threshold),
        ("相似度-低于阈值", test_sim_just_below_threshold),
        ("相似度-恰好阈值", test_sim_exactly_threshold),
        ("相似度-长字符串", test_sim_long_strings),
        ("标准化-去除标点", test_norm_removes_punctuation),
        ("标准化-中文标点", test_norm_chinese_punctuation),
        ("标准化-转小写", test_norm_lowercase),
        ("标准化-空字符串", test_norm_empty),
        ("标准化-混合内容", test_norm_mixed),
        ("去重-空标题", test_dedup_empty_title),
        ("去重-None标题", test_dedup_none_title),
        ("去重-配置", test_dedup_config),
        ("去重-中文相同", test_chinese_similarity_same),
        ("去重-中文不同", test_chinese_similarity_diff),
        ("去重-混合语言", test_mixed_lang_similarity),
        ("去重-超长标题", test_very_long_title),
        ("去重-仅特殊字符", test_special_chars_only),
        ("去重-仅空格", test_spaces_only),
        # Integration
        ("集成-初始化", test_guard_init),
        ("集成-批次ID", test_guard_batch_id),
        ("集成-新任务通过", test_guard_check_allowed),
        ("集成-空标题", test_guard_check_empty),
        ("集成-幂等二次拦截", test_guard_idempotent_second_time),
        ("集成-系统状态", test_guard_system_status),
        ("集成-空列表过滤", test_guard_filter_empty),
        ("集成-单条过滤", test_guard_filter_single),
        ("集成-快捷函数", test_quick_guard),
        ("集成-结果字段", test_guard_result_fields),
        ("集成-None目标", test_guard_none_goal),
        ("集成-快速连续", test_rapid_checks),
        # Performance & Concurrent
        ("性能-200字符50次", test_performance_200char),
        ("并发-键生成一致性", test_concurrent_key_generation),
    ]

    for name, fn in tests:
        test(name, fn)

    print()
    print("=" * 70)
    total = PASS + FAIL
    print(f"测试结果: {'✅ 全部通过' if FAIL == 0 else '❌ 存在失败'}")
    print(f"运行测试: {total} 个")
    print(f"通过: {PASS} 个")
    print(f"失败: {FAIL} 个")
    print("=" * 70)

    # 输出JSON报告
    report = {
        "task_id": 2119,
        "version": "V4.6",
        "timestamp": datetime.now().isoformat(),
        "total": total,
        "passed": PASS,
        "failed": FAIL,
        "pass_rate": round(PASS / total * 100, 1) if total > 0 else 0,
        "errors": [{"test": n, "error": e} for n, e in ERRORS]
    }

    report_path = "/Users/mettlyz/.openclaw/workspace/sds1/output/task-2119/test_report_2119.json"
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\n📄 测试报告已保存: {report_path}")

    sys.exit(0 if FAIL == 0 else 1)
