#!/usr/bin/env python3
"""Task 2120: AI半导体材料概念股2026年Q2财报前瞻与持仓优化方案"""
import sys, os, json, urllib.request

def search(query, max_results=10):
    api_key = os.environ.get("TAVILY_API_KEY") or "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"
    payload = json.dumps({
        "query": query,
        "max_results": int(max_results),
        "search_depth": "advanced",
        "include_answer": True,
    }).encode()
    req = urllib.request.Request(
        "https://api.tavily.com/search",
        data=payload,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode())

# 执行多个搜索查询
queries = [
    "A股半导体材料板块 2026年Q1财报 光刻胶 湿电子化学品 CMP抛光材料",
    "AI芯片材料市场规模 2026 450亿美元 行业分析",
    "半导体材料概念股 20家核心标的 2026 Q1业绩",
    "半导体材料行业估值对比 2026 营收增速 毛利率",
]

all_results = {}
for i, q in enumerate(queries):
    # print(f"搜索 {i+1}/{len(queries)}: {q}")
    try:
        result = search(q, 10)
        all_results[f"query_{i}"] = result
        # print(f"  完成，获得 {len(result.get('results', []))} 条结果")
    except Exception as e:
        # print(f"  错误: {e}")

# 保存搜索结果
with open("/Users/mettlyz/.openclaw/workspace/output/task-2120/tavily_results.json", "w", encoding="utf-8") as f:
    json.dump(all_results, f, ensure_ascii=False, indent=2)

# print("搜索完成，结果已保存")
