#!/usr/bin/env python3
"""
修复 get_llm_stats API，从 token_usage 表计算总费用
"""

import os

app_path = os.path.join(os.path.dirname(__file__), 'app.py')
with open(app_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 旧的 stats 计算代码
old_stats = '''        # 费用统计 (使用 input_cost 和 output_cost 计算)
        c.execute('SELECT SUM(input_cost + output_cost) FROM llm_configs')
        total_cost = c.fetchone()[0] or 0
        
        # 今日费用 (token_usage 表使用 timestamp 字段和 cost_usd)
        c.execute("SELECT SUM(cost_usd) FROM token_usage WHERE date(timestamp) = date('now')")
        today_cost = c.fetchone()[0] or 0
        
        # 本月费用
        c.execute("SELECT SUM(cost_usd) FROM token_usage WHERE strftime('%Y-%m', timestamp) = strftime('%Y-%m', 'now')")
        month_cost = c.fetchone()[0] or 0'''

# 新的 stats 计算代码（统一从 token_usage 表获取）
new_stats = '''        # 费用统计 (统一从 token_usage 表获取)
        c.execute('SELECT SUM(cost_usd) FROM token_usage')
        total_cost = c.fetchone()[0] or 0
        
        # 今日费用
        c.execute("SELECT SUM(cost_usd) FROM token_usage WHERE date(timestamp) = date('now')")
        today_cost = c.fetchone()[0] or 0
        
        # 本月费用
        c.execute("SELECT SUM(cost_usd) FROM token_usage WHERE strftime('%Y-%m', timestamp) = strftime('%Y-%m', 'now')")
        month_cost = c.fetchone()[0] or 0'''

if old_stats in content:
    content = content.replace(old_stats, new_stats)
    print("✅ 已修复 get_llm_stats API")
else:
    print("❌ 未找到要替换的代码")
    import sys
    sys.exit(1)

# 保存
with open(app_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ app.py 已更新")
