#!/usr/bin/env python3
import sys, os, json, urllib.request

def search(query, max_results=5):
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
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode())

# 搜索1
result1 = search("2026 AI Agent autonomous agent latest technology progress system architecture", 10)
print("=== Search 1 ===")
print(json.dumps(result1, ensure_ascii=False, indent=2))

# 搜索2
result2 = search("2026 multi-agent system LLM agent framework OpenAI Anthropic", 8)
print("\n=== Search 2 ===")
print(json.dumps(result2, ensure_ascii=False, indent=2))

# 搜索3
result3 = search("2026 agentic AI reasoning planning memory architecture", 8)
print("\n=== Search 3 ===")
print(json.dumps(result3, ensure_ascii=False, indent=2))
