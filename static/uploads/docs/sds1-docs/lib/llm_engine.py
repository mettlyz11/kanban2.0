#!/usr/bin/env python3
"""
LLM引擎 - 提取自subagent_executor.py
"""

import os
import re
import json
from pathlib import Path

class RealLLMEngine:
    """真实LLM推理引擎"""
    
    def __init__(self):
        config_path = Path.home() / '.openclaw' / 'openclaw.json'
        with open(config_path) as f:
            cfg = json.load(f)
        
        providers = cfg.get('models', {}).get('providers', {})
        atp = providers.get('alitokenplan', {})
        acp = providers.get('alicodingplan', {})
        ds = providers.get('deepseek', {})
        ms = providers.get('moonshot', {})
        hsc = providers.get('huoshanCoding', {})
        dmx = providers.get('dmxapi', {})
        
        self.models_to_try = [
            {'name': 'alitokenplan',   'base_url': atp.get('baseUrl'), 'model': 'qwen3.6-plus',             'headers': atp.get('headers', {}), 'timeout': 60},
            {'name': 'alicodingplan',  'base_url': acp.get('baseUrl'), 'model': 'kimi-k2.5',                'headers': acp.get('headers', {}), 'timeout': 60},
            {'name': 'deepseek',       'base_url': ds.get('baseUrl'),  'model': 'deepseek-chat',            'headers': ds.get('headers', {}), 'timeout': 60},
            {'name': 'moonshot',       'base_url': ms.get('baseUrl'),  'model': 'kimi-k2.6',                'headers': ms.get('headers', {}), 'timeout': 60},
            {'name': 'huoshanCoding',  'base_url': hsc.get('baseUrl'), 'model': 'ark-code-latest',          'headers': hsc.get('headers', {}), 'timeout': 60},
            {'name': 'dmxapi',         'base_url': dmx.get('baseUrl'), 'model': 'gpt-5.4',                  'headers': dmx.get('headers', {}), 'timeout': 60},
        ]
        self.used_model = None
    
    def call_llm(self, prompt: str, max_tokens: int = 2000, temperature: float = 0.7) -> str:
        import requests
        
        for model_cfg in self.models_to_try:
            if not model_cfg.get('base_url'):
                continue
            try:
                url = f"{model_cfg['base_url']}/chat/completions"
                headers = {'Content-Type': 'application/json', **model_cfg.get('headers', {})}
                
                # 替换环境变量
                for k, v in list(headers.items()):
                    if '${' in str(v):
                        def replace_env(m):
                            ev = m.group(1).strip()
                            val = os.environ.get(ev, '')
                            if not val:
                                ef = Path.home() / '.openclaw' / '.env'
                                if ef.exists():
                                    with open(ef) as f:
                                        for line in f:
                                            if '=' in line and line.split('=')[0].strip() == ev:
                                                val = line.split('=', 1)[1].strip()
                                                break
                            return val
                        headers[k] = re.sub(r'\$\{([^}]+)\}', replace_env, v)
                
                payload = {
                    'model': model_cfg['model'],
                    'messages': [
                        {'role': 'system', 'content': '你是一个专业的AI执行助手，擅长分析任务并决定最佳执行策略。'},
                        {'role': 'user', 'content': prompt}
                    ],
                    'max_tokens': max_tokens,
                    'temperature': temperature
                }
                
                resp = requests.post(url, json=payload, headers=headers, timeout=model_cfg.get('timeout', 15))
                if resp.status_code == 200:
                    result = resp.json()
                    if result and result.get('choices'):
                        content = result['choices'][0].get('message', {}).get('content', '')
                        if content:
                            self.used_model = model_cfg['name']
                            return content.strip()
            except Exception:
                continue
        
        raise Exception("所有LLM模型调用失败")
