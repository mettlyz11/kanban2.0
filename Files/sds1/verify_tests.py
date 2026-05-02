#!/usr/bin/env python3
"""快速验证核心逻辑"""
import sys
sys.path.insert(0, '/Users/mettlyz/.openclaw/workspace/scripts')
sys.path.insert(0, '/Users/mettlyz/.openclaw/workspace/sds')
sys.path.insert(0, '/Users/mettlyz/.openclaw/workspace/sds/core')

from core.task_generation_guard_v46 import (
    IdempotencyLayer, RateLimitLayer, SemanticDedupLayer,
    TaskGenerationGuard, GuardDecision
)
import tempfile, os, time

results = []

# Test 1: 幂等性键确定性
layer = IdempotencyLayer(log_file=tempfile.mktemp())
k1 = layer.generate_key("测试", 1, "desc")
k2 = layer.generate_key("测试", 1, "desc")
assert k1 == k2 and len(k1) == 16, "幂等键确定性失败"
results.append("✅ 幂等键确定性")

# Test 2: 记录与检查
tf = tempfile.mktemp()
l2 = IdempotencyLayer(log_file=tf)
key = l2.generate_key("重复", 99)
l2.record(key, 12345, "重复", 99)
r = l2.check(key)
assert not r['is_safe'] and r['local_task_id'] == 12345, "幂等检查失败"
results.append("✅ 幂等记录与检查")

# Test 3: 频率限制配置
rl = RateLimitLayer(max_tasks=2, max_pending=3)
assert rl.max_tasks == 2 and rl.max_pending == 3, "频率配置失败"
results.append("✅ 频率限制配置")

# Test 4: Levenshtein距离
d = SemanticDedupLayer.levenshtein_distance
assert d("", "") == 0, "空字符串距离失败"
assert d("abc", "abc") == 0, "相同字符串距离失败"
assert d("abc", "abcd") == 1, "插入距离失败"
assert d("cat", "bat") == 1, "替换距离失败"
results.append("✅ Levenshtein距离")

# Test 5: 相似度计算
s = SemanticDedupLayer.string_similarity
assert s("", "") == 1.0, "空串相似度失败"
assert s("test", "test") == 1.0, "相同串相似度失败"
# 100字符差15个: 0.85
s1 = "A" * 100
s2 = "A" * 85 + "B" * 15
assert abs(s("A"*100, "A"*85+"B"*15) - 0.85) < 0.001, "阈值边界相似度失败"
results.append("✅ 相似度阈值边界")

# Test 6: 文本标准化
n = SemanticDedupLayer.normalize_text
assert n("Hello, World!") == "helloworld"
assert n("你好，世界！") == "你好世界"
assert n("") == ""
assert n(None) == ""
results.append("✅ 文本标准化")

# Test 7: Guard初始化
guard = TaskGenerationGuard()
assert guard.config['max_tasks_per_24h'] == 2
assert guard.config['similarity_threshold'] == 0.85
assert guard.batch_id.startswith('V46-')
results.append("✅ Guard初始化配置")

# Test 8: Guard检查新任务
title = f"唯一任务_{time.time()}"
result = guard.check(title, 999)
assert result.decision == GuardDecision.ALLOWED
assert result.can_generate
results.append("✅ Guard新任务通过")

# Test 9: Guard幂等拦截
guard2 = TaskGenerationGuard()
title2 = f"幂等测试_{time.time()}"
r1 = guard2.check(title2, 888)
assert r1.decision == GuardDecision.ALLOWED
guard2.idempotency.record(r1.idempotency_key, 99999, title2, 888)
r2 = guard2.check(title2, 888)
assert r2.decision == GuardDecision.BLOCKED_IDEMPOTENT
results.append("✅ Guard幂等拦截")

# Test 10: 空列表过滤
passed, blocked = guard.filter_recommendations([])
assert len(passed) == 0 and len(blocked) == 0
results.append("✅ 空列表过滤")

# Test 11: 并发键生成
import threading
keys = []
def gen_key(): keys.append(IdempotencyLayer.generate_key("并发测试", 1))
threads = [threading.Thread(target=gen_key) for _ in range(10)]
for t in threads: t.start()
for t in threads: t.join()
assert len(set(keys)) == 1, "并发键不一致"
results.append("✅ 并发键生成一致性")

# Test 12: 零频率上限
zero_rl = RateLimitLayer(max_tasks=0)
r = zero_rl.check_rate_limit(1)
assert not r['can_generate'], "零上限应拦截"
results.append("✅ 零频率上限拦截")

print("\n" + "=" * 60)
print("验证结果汇总")
print("=" * 60)
for r in results:
    print(r)
print(f"\n✅ 全部 {len(results)} 项验证通过！")
