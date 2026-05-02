#!/usr/bin/env python3
import os
import json
import requests

API_KEY = os.environ.get('TAVILY_API_KEY') or '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'

def search(query, max_results=10):
    url = "https://api.tavily.com/search"
    payload = {
        "query": query,
        "max_results": max_results,
        "search_depth": "advanced",
        "include_answer": True
    }
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    response = requests.post(url, json=payload, headers=headers)
    return response.json()

# 搜索轮次1：AI材料科学融资
queries = [
    "AI材料科学 天使轮融资 2025 2026",
    "AI for Science startup funding angel round 2025 2026",
    "AI生物科技 初创公司 融资 2025",
    "AI能源技术 Pre-A轮 2025 2026",
    "Periodic Labs 融资 估值 70亿",
    "AI催化 初创公司 天使投资 2025",
    "AI药物发现 天使轮融资 2025",
    "AI新材料 创业公司 融资名单 2025"
]

all_results = []
for q in queries:
    print(f"Searching: {q}")
    result = search(q, max_results=8)
    all_results.append({
        "query": q,
        "answer": result.get('answer', ''),
        "results": result.get('results', [])
    })

with open('/Users/mettlyz/.openclaw/workspace/output/task-1959/search_results.json', 'w') as f:
    json.dump(all_results, f, ensure_ascii=False, indent=2)

print("Search completed, results saved")
