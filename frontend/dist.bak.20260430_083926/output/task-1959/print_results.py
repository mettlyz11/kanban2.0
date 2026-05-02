#!/usr/bin/env python3
import json

with open('/Users/mettlyz/.openclaw/workspace/output/task-1959/raw_search.json') as f:
    data = json.load(f)

for q, r in data.items():
    print(f"\n=== {q} ===")
    for item in r.get('results', []):
        print(f"  [{item['title']}] {item['url']}")
        print(f"  {item['content'][:300]}")
        print()
