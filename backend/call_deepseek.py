#!/usr/bin/env python3
"""Separate process for DeepSeek API call - avoids eventlet DNS issues"""
import json, urllib.request, sys

task_desc = sys.argv[1] if len(sys.argv) > 1 else ""
api_key = sys.argv[2] if len(sys.argv) > 2 else ""

prompt = f"""你是一个项目管理助手，请为以下任务生成一段人话摘要，不超过5行。
要求：1) 说清楚这是干什么的 2) 现在状态如何 3) 产出/进展 4) 下一步建议

{task_desc}"""

body = json.dumps({
    "model": "deepseek-chat",
    "messages": [{"role": "user", "content": prompt}],
    "max_tokens": 300,
    "temperature": 0.3
}).encode()

req = urllib.request.Request(
    "https://api.deepseek.com/v1/chat/completions",
    data=body,
    headers={
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
)

try:
    result = json.loads(urllib.request.urlopen(req, timeout=30).read())
    # print(result["choices"][0]["message"]["content"].strip())
except Exception as e:
    # print(f"__ERROR__:{e}")
    sys.exit(1)
