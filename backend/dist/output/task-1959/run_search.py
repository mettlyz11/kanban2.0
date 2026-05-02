#!/usr/bin/env python3
"""Tavily search wrapper for investment research."""
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
    with urllib.request.urlopen(req, timeout=90) as resp:
        return json.loads(resp.read().decode())

if __name__ == "__main__":
    queries = [
        "2025 2026 AI 材料科学 天使轮 Pre-A 融资 中国初创公司",
        "2025 AI for Science 生物科技 融资 初创企业",
        "2025 2026 AI 新能源 电池 材料 天使轮融资",
        "Periodic Labs AI materials 融资 70亿估值",
        "2025 China AI drug discovery biotech angel funding",
        "AI 催化剂 材料 初创公司 2025 融资",
        "天使投资渠道 FA 天使联盟 社群 AI for Science",
        "2025 2026 一级市场 AI 材料 生物 能源 融资事件",
    ]
    
    all_results = []
    for i, q in enumerate(queries):
        print(f"=== Search {i+1}/{len(queries)}: {q} ===")
        try:
            result = search(q, 15)
            all_results.append({
                "query": q,
                "answer": result.get("answer", ""),
                "results": result.get("results", [])
            })
            print(f"Got {len(result.get('results', []))} results")
        except Exception as e:
            print(f"Error: {e}")
    
    with open('/Users/mettlyz/.openclaw/workspace/output/task-1959/search_results.json', 'w') as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    
    print("\n=== Search complete ===")
    print(f"Total searches: {len(all_results)}")
