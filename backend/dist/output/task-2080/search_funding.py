#!/usr/bin/env python3
import json
import os
import re
import pathlib
import urllib.request

TAVILY_URL = "https://api.tavily.com/search"

def load_key():
    key = os.environ.get("TAVILY_API_KEY")
    if key:
        return key.strip()
    env_path = pathlib.Path.home() / ".openclaw" / ".env"
    if env_path.exists():
        txt = env_path.read_text(encoding="utf-8", errors="ignore")
        m = re.search(r"^\s*TAVILY_API_KEY\s*=\s*(.+?)\s*$", txt, re.M)
        if m:
            v = m.group(1).strip().strip('"').strip("'")
            if v:
                return v
    return None

def search(query, max_results=10):
    key = load_key()
    payload = {
        "api_key": key,
        "query": query,
        "max_results": max_results,
        "search_depth": "advanced",
        "include_answer": True,
        "include_images": False,
        "include_raw_content": False,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        TAVILY_URL, data=data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))

# Search queries
queries = [
    "AI materials science startup funding 2026 Q1 Q2",
    "AI for materials discovery venture capital 2026",
    "computational materials science funding rounds 2026",
    "AI battery materials startup investment 2026",
    "machine learning materials science company funding 2026",
]

all_results = []
for q in queries:
    print(f"Searching: {q}")
    try:
        result = search(q, max_results=8)
        all_results.append({"query": q, "data": result})
    except Exception as e:
        print(f"Error: {e}")

with open("/Users/mettlyz/.openclaw/workspace/output/task-2080/search_results.json", "w") as f:
    json.dump(all_results, f, indent=2, ensure_ascii=False)

print("Search completed!")
