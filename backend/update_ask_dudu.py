#!/usr/bin/env python3
"""
更新 ask_dudu 函数以记录 token 使用
"""

import os
import re

app_path = os.path.join(os.path.dirname(__file__), 'app.py')
with open(app_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 旧的 ask_dudu 函数（部分）
old_code = '''            if res.status_code == 200:
                result = res.json()
                response = result.get('choices', [{}])[0].get('message', {}).get('content', '')
            else:
                # 如果 Gateway 不可用，使用模拟回复
                response = f"[OpenClaw 服务暂时不可用]\\n\\n你的消息：{message[:100]}"'''

# 新的 ask_dudu 函数（部分）
new_code = '''            if res.status_code == 200:
                result = res.json()
                response = result.get('choices', [{}])[0].get('message', {}).get('content', '')
                
                # 📊 记录 token 使用和费用
                usage = result.get('usage', {})
                prompt_tokens = usage.get('prompt_tokens', 0)
                completion_tokens = usage.get('completion_tokens', 0)
                if prompt_tokens > 0 or completion_tokens > 0:
                    record_token_usage(
                        provider='moonshot',
                        model='kimi-k2.5',
                        prompt_tokens=prompt_tokens,
                        completion_tokens=completion_tokens
                    )
            else:
                # 如果 Gateway 不可用，使用模拟回复
                response = f"[OpenClaw 服务暂时不可用]\\n\\n你的消息：{message[:100]}"'''

if old_code in content:
    content = content.replace(old_code, new_code)
    print("✅ 已更新 ask_dudu 函数以记录 token 使用")
else:
    print("❌ 未找到要替换的代码")
    print("查找的代码片段:")
    print(old_code[:200])
    import sys
    sys.exit(1)

# 保存
with open(app_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ app.py 已更新")
