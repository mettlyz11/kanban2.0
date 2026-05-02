
#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'core'))

from core.task_generation_guard_v46 import (
    IdempotencyLayer,
    RateLimitLayer,
    SemanticDedupLayer,
    TaskGenerationGuard,
)

print("="*70)
print("🧪 SDS任务生成三重保障系统 V4.6 - 快速验证测试")
print("="*70)

# 1. 幂等性测试
print("\n1️⃣ 幂等性保障测试...")
idem = IdempotencyLayer()
k1 = idem.generate_key("测试任务", 75, "描述")
k2 = idem.generate_key("测试任务", 75, "描述")
assert k1 == k2, "相同输入应生成相同键"
print(f"   ✅ 幂等键生成: {k1[:16]}...")
print("   ✅ 相同输入键一致")

# 2. 频率限制测试
print("\n2️⃣ 频率限制测试...")
rate = RateLimitLayer(max_tasks=2, max_pending=3)
result = rate.check_rate_limit(999999)
assert 'can_generate' in result, "频率限制应返回can_generate字段"
print(f"   ✅ 频率限制返回结构正确")
print(f"   ✅ 配置验证通过: 24小时={rate.max_tasks}任务, pending={rate.max_pending}")

# 3. 语义去重测试
print("\n3️⃣ 语义去重测试...")
dedup = SemanticDedupLayer(prefix_length=15, similarity_threshold=0.85)
sim = dedup.string_similarity("相同字符串", "相同字符串")
assert sim == 1.0, "相同字符串相似度应为1.0"
print(f"   ✅ 相似度计算正确: {sim}")

# Levenshtein距离测试
dist = dedup.levenshtein_distance("cat", "bat")
assert dist == 1, "单字符替换距离应为1"
print(f"   ✅ Levenshtein距离正确: cat→bat = {dist}")

# 前缀长度测试
assert dedup.prefix_length == 15, "前缀长度应为15"
print(f"   ✅ 标题前缀长度配置正确: {dedup.prefix_length}字")

# 4. 集成测试
print("\n4️⃣ 三重保障集成测试...")
guard = TaskGenerationGuard()
result = guard.check("唯一测试任务_12345", 999, "测试描述")
assert result.can_generate, "新任务应可生成"
assert result.idempotency_key is not None, "应返回幂等键"
print(f"   ✅ 集成检查通过，决策: {result.decision.value}")
print(f"   ✅ 批次ID: {guard.batch_id}")

# 5. 系统状态检查
print("\n5️⃣ 系统状态检查...")
status = guard.get_system_status()
assert 'version' in status, "状态应包含版本"
print(f"   ✅ 版本: {status['version']}")
print(f"   ✅ 各目标状态检查完成")

print("\n" + "="*70)
print("✅ 所有核心功能测试通过!")
print("="*70)
print("\n📋 保障系统已部署:")
print("   • Layer 1: 幂等性保障 (SHA-256确定性键)")
print("   • Layer 2: 频率限制 (每目标24小时最多2任务)")
print("   • Layer 3: 语义去重 (15字前缀+0.85相似度)")
print("   • Pending水位控制 (每目标最多3个)")
print("   • 审计日志完整记录")
