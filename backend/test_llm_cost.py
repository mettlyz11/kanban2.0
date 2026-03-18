#!/usr/bin/env python3
"""
测试 LLM 费用记录机制
"""

import sys
sys.path.insert(0, '.')

from app import calculate_cost, record_token_usage, app

print("=" * 60)
print("🧪 LLM 费用记录机制测试")
print("=" * 60)
print()

# 测试 1: 费用计算
print("1️⃣ 测试费用计算功能")
print("-" * 60)
test_cases = [
    ('kimi-k2.5', 1000, 500, 0.006),
    ('qwen3.5-plus', 2000, 1000, 0.015),
    ('gpt-4o', 1500, 800, 0.0195),
    ('deepseek-chat', 5000, 2000, 0.00355),
]

all_pass = True
for model, input_t, output_t, expected in test_cases:
    cost = calculate_cost(model, input_t, output_t)
    status = "✅" if abs(cost - expected) < 0.0001 else "❌"
    print(f"  {status} {model}: {input_t}+{output_t} tokens = ${cost:.6f} (期望：${expected:.6f})")
    if abs(cost - expected) >= 0.0001:
        all_pass = False

print()

# 测试 2: 记录 token 使用
print("2️⃣ 测试 token 使用记录")
print("-" * 60)
try:
    record_token_usage('moonshot', 'kimi-k2.5', 1000, 500)
    print("  ✅ 记录成功")
except Exception as e:
    print(f"  ❌ 记录失败：{e}")
    all_pass = False

print()

# 测试 3: API 返回数据
print("3️⃣ 测试 API 数据返回")
print("-" * 60)
with app.test_client() as client:
    # 测试 stats API
    response = client.get('/api/llm/stats')
    data = response.get_json()
    if data['success']:
        stats = data['stats']
        print(f"  ✅ Stats API 正常")
        print(f"     今日费用：${stats['today_cost']}")
        print(f"     本月费用：${stats['month_cost']}")
        print(f"     累计费用：${stats['total_cost']}")
    else:
        print(f"  ❌ Stats API 失败：{data.get('error')}")
        all_pass = False
    
    # 测试 token-usage API
    response = client.get('/api/llm/token-usage?limit=3')
    data = response.get_json()
    if data['success']:
        print(f"  ✅ Token Usage API 正常")
        print(f"     记录数：{data['count']}")
        if data['usage']:
            latest = data['usage'][0]
            print(f"     最新记录：{latest['model']} - {latest['total_tokens']} tokens - ${latest['cost']}")
    else:
        print(f"  ❌ Token Usage API 失败：{data.get('error')}")
        all_pass = False

print()
print("=" * 60)
if all_pass:
    print("✅ 所有测试通过！LLM 费用记录机制正常工作")
else:
    print("❌ 部分测试失败")
print("=" * 60)
