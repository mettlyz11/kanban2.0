#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, '/Users/mettlyz/.openclaw/workspace/tools')
from tavily_search import search

# Search 1: Market size and funding
print("=== Search 1: AI Materials Science Market Size 2026 ===")
result1 = search("2026 AI materials science market size funding valuation", 10)
print(result1)
print("\n\n")

# Search 2: Active investors in materials science
print("=== Search 2: VC Investors Materials Science Hard Tech 2026 ===")
result2 = search("VC firms investing in materials science hard tech deep tech 2026", 10)
print(result2)
print("\n\n")

# Search 3: China AI materials science
print("=== Search 3: China AI materials science startups funding ===")
result3 = search("中国AI材料科学 初创公司 融资 2025 2026", 10)
print(result3)
