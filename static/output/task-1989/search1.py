import requests
import json

api_key = "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"

queries = [
    "gold ETF fund flows 2026 April China Asia Western divergence SPDR GLD",
    "华安黄金ETF 518880 博时黄金ETF 159937 资金流向 溢价率 2026年4月",
    "gold price technical analysis 3044 key support resistance 2026",
    "China gold ETF inflows record Q1 2026"
]

results_all = {}
for q in queries:
    try:
        resp = requests.post(
            "https://api.tavily.com/search",
            headers={"Content-Type": "application/json"},
            json={"api_key": api_key, "query": q, "max_results": 3, "search_depth": "basic"},
            timeout=20
        )
        data = resp.json()
        answer = data.get("answer") or ""
        results = data.get("results") or []
        results_all[q] = {
            "answer": answer,
            "results": [{"title": r.get("title",""), "url": r.get("url",""), "content": (r.get("content") or "")[:500]} for r in results]
        }
        # print(f"\n=== {q} ===")
        # print("Answer:", answer[:400] if answer else "N/A")
        for r in results[:2]:
            # print(f"  - {r.get('title','')}: {(r.get('content') or '')[:200]}")
    except Exception as e:
        # print(f"Error for {q}: {e}")
        results_all[q] = {"error": str(e)}

with open("/Users/mettlyz/.openclaw/workspace/output/task-1989/search_results.json", "w", encoding="utf-8") as f:
    json.dump(results_all, f, ensure_ascii=False, indent=2)

# print("\n搜索完成")
