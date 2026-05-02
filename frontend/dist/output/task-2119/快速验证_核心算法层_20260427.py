#!/usr/bin/env python3
"""SDS V4.6 核心算法层快速验证脚本（无DB依赖）"""
import sys, os, tempfile, time, threading, json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "sds" / "core"))
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from task_generation_guard_v46 import (
    IdempotencyLayer, RateLimitLayer, SemanticDedupLayer,
    TaskGenerationGuard, GuardDecision
)

def test_idempotency():
    tmp = tempfile.mkdtemp()
    logf = os.path.join(tmp, 'test.log')
    layer = IdempotencyLayer(log_file=logf)
    
    # 确定性
    k1 = layer.generate_key("测试", 1, "desc")
    k2 = layer.generate_key("测试", 1, "desc")
    assert k1 == k2 and len(k1) == 16, "幂等键应确定且16位"
    
    # 不同输入不同键
    assert layer.generate_key("A", 1) != layer.generate_key("B", 1), "不同标题不同键"
    assert layer.generate_key("T", 1) != layer.generate_key("T", 2), "不同goal不同键"
    
    # 检查与记录
    assert layer.check(k1)['is_safe'] == True, "新键应安全"
    layer.record(k1, 100, "测试", 1)
    assert layer.check(k1)['is_safe'] == False, "已记录应拦截"
    assert layer.check(k1)['local_task_id'] == 100, "应返回task_id"
    
    # 并发一致性
    keys = []
    def gen(): keys.append(IdempotencyLayer.generate_key("并发", 1))
    ts = [threading.Thread(target=gen) for _ in range(10)]
    for t in ts: t.start()
    for t in ts: t.join()
    assert len(set(keys)) == 1, "并发键应一致"
    
    print("  ✅ IdempotencyLayer: 6/6 通过")
    return True

def test_rate_limit():
    layer = RateLimitLayer(max_tasks=2, max_pending=3, window_hours=24)
    
    assert layer.max_tasks == 2, "默认max_tasks=2"
    assert layer.max_pending == 3, "默认max_pending=3"
    assert layer.window_hours == 24, "默认window=24h"
    
    # 结构检查
    r = layer.check_rate_limit(999999)
    for f in ['can_generate','current_count','max_allowed','remaining_slots','window_hours','window_start','goal_id','check_type']:
        assert f in r, f"缺少字段 {f}"
    
    r = layer.check_all(999999)
    assert 'can_generate' in r and 'blocked_reason' in r, "组合检查结构"
    
    # 边界
    zero = RateLimitLayer(max_tasks=0)
    assert zero.check_rate_limit(1)['can_generate'] == False, "零上限应拦截"
    
    large = RateLimitLayer(max_tasks=10000)
    assert large.check_rate_limit(1)['remaining_slots'] >= 9999, "大上限应允许"
    
    print("  ✅ RateLimitLayer: 6/6 通过")
    return True

def test_semantic_dedup():
    layer = SemanticDedupLayer(prefix_length=15, similarity_threshold=0.85)
    
    # Levenshtein
    assert layer.levenshtein_distance("abc", "abc") == 0, "相同距离0"
    assert layer.levenshtein_distance("cat", "bat") == 1, "单替换距离1"
    assert layer.levenshtein_distance("abc", "abcd") == 1, "插入距离1"
    assert layer.levenshtein_distance("abcd", "abc") == 1, "删除距离1"
    
    # 相似度
    assert layer.string_similarity("test", "test") == 1.0, "相同=1.0"
    assert layer.string_similarity("", "") == 1.0, "双空=1.0"
    assert layer.string_similarity("a", "") == 0.0, "单空=0.0"
    
    # 阈值边界
    s1, s2 = "A"*100, "A"*85 + "B"*15
    assert layer.string_similarity(s1, s2) == 0.85, "恰好0.85"
    
    s1, s2 = "ABCDEFGHIJ1234567890", "ABCDEFGHIJ12345678XX"
    assert layer.string_similarity(s1, s2) > 0.85, "高于0.85"
    
    # 标准化
    assert layer.normalize_text("Hello, World!") == "helloworld", "去标点"
    assert layer.normalize_text("你好，世界！") == "你好世界", "去中文标点"
    assert layer.normalize_text("HELLO") == "hello", "转小写"
    
    # 空输入
    assert layer.check("")['is_duplicate'] == False, "空标题不重复"
    assert layer.check(None)['is_duplicate'] == False, "None不重复"
    
    # 性能
    s1, s2 = "A"*200, "A"*193 + "B"*7
    t0 = time.time()
    for _ in range(50): layer.string_similarity(s1, s2)
    elapsed = time.time() - t0
    assert elapsed < 3.0, f"50次200字符应<3秒, 实际{elapsed:.2f}秒"
    
    print(f"  ✅ SemanticDedupLayer: 13/13 通过 (性能: {elapsed/50*1000:.1f}ms/次)")
    return True

def test_integration():
    guard = TaskGenerationGuard()
    
    assert guard.config['max_tasks_per_24h'] == 2
    assert guard.config['similarity_threshold'] == 0.85
    assert guard.config['prefix_length'] == 15
    assert guard.batch_id.startswith('V46-')
    
    # 新任务通过
    unique = f"唯一测试_{time.time()}"
    r = guard.check(unique, 999, "测试")
    assert r.decision == GuardDecision.ALLOWED, "新任务应通过"
    assert r.can_generate == True
    assert r.idempotency_key is not None
    
    # 幂等拦截
    guard.idempotency.record(r.idempotency_key, 99999, unique, 999)
    r2 = guard.check(unique, 999, "测试")
    assert r2.decision == GuardDecision.BLOCKED_IDEMPOTENT, "重复应被幂等拦截"
    
    # 空列表过滤
    p, b = guard.filter_recommendations([])
    assert len(p) == 0 and len(b) == 0
    
    print("  ✅ TaskGenerationGuard集成: 6/6 通过")
    return True

if __name__ == "__main__":
    print("=" * 60)
    print("SDS V4.6 核心算法层快速验证")
    print("=" * 60)
    
    all_pass = True
    all_pass &= test_idempotency()
    all_pass &= test_rate_limit()
    all_pass &= test_semantic_dedup()
    all_pass &= test_integration()
    
    print("=" * 60)
    print(f"{'✅ 全部通过' if all_pass else '❌ 存在失败'}")
    print("=" * 60)
    sys.exit(0 if all_pass else 1)
