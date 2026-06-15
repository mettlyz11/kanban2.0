#!/usr/bin/env python3
import sys
sys.path.insert(0, '/Users/mettlyz/.openclaw/workspace/tools')
sys.path.insert(0, '/Users/mettlyz/.openclaw/workspace')
import json
import os
import urllib.request
import urllib.parse

API_KEY = "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"

def search(query, max_results=10):
    url = "https://api.tavily.com/search"
    payload = json.dumps({
        "api_key": API_KEY,
        "query": query,
        "max_results": max_results,
        "search_depth": "advanced"
    }).encode()
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())

queries = [
    "AI materials science startups angel pre-A funding 2025",
    "AI for science startup investment 2025 2026 materials biology energy",
    "人工智能材料科学初创公司 天使轮 2025 融资",
    "AI催化剂 AI新材料 初创公司 融资 2025 2026",
    "Periodic Labs competitors AI materials startup funding",
    "AI drug discovery startup angel funding 2025 2026",
    "AI energy storage battery startup funding 2025",
]

results = {}
for q in queries:
    try:
        r = search(q, 8)
        results[q] = r
        # print(f"✅ {q[:50]}: {len(r.get('results',[]))} results")
    except Exception as e:
        # print(f"❌ {q[:50]}: {e}")

with open('/Users/mettlyz/.openclaw/workspace/output/task-1959/raw_search.json', 'w') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)

# print("Done! Saved to raw_search.json")
