#!/usr/bin/env python3
"""
修复 LLM 费用记录机制
1. 添加费用计算函数
2. 添加 token 使用记录函数
3. 更新 ask_dudu API 记录费用
"""

import os
import sys

# 读取 app.py
app_path = os.path.join(os.path.dirname(__file__), 'app.py')
with open(app_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 要插入的代码
llm_utils_code = '''
# ============================================
# LLM 费用记录工具函数
# ============================================

# 模型价格表 (USD per 1K tokens)
MODEL_PRICES = {
    # Kimi / Moonshot
    'kimi-k2.5': {'input': 0.002, 'output': 0.008},
    'kimi-k2': {'input': 0.002, 'output': 0.008},
    'moonshot-v1-8k': {'input': 0.012, 'output': 0.012},
    'moonshot-v1-32k': {'input': 0.024, 'output': 0.024},
    'moonshot-v1-128k': {'input': 0.06, 'output': 0.06},
    
    # Qwen / 阿里云
    'qwen3.5-plus': {'input': 0.003, 'output': 0.009},
    'qwen3-plus': {'input': 0.003, 'output': 0.009},
    'qwen-max': {'input': 0.04, 'output': 0.12},
    'qwen-plus': {'input': 0.004, 'output': 0.012},
    'qwen-turbo': {'input': 0.001, 'output': 0.003},
    
    # DeepSeek
    'deepseek-chat': {'input': 0.00027, 'output': 0.0011},
    'deepseek-coder': {'input': 0.00027, 'output': 0.0011},
    'deepseek-v3': {'input': 0.00027, 'output': 0.0011},
    
    # GLM / 智谱
    'glm-4': {'input': 0.014, 'output': 0.014},
    'glm-4-air': {'input': 0.001, 'output': 0.001},
    'glm-4-flash': {'input': 0.00014, 'output': 0.00014},
    'glm-5': {'input': 0.014, 'output': 0.014},
    
    # GPT / OpenAI
    'gpt-4o': {'input': 0.005, 'output': 0.015},
    'gpt-4o-mini': {'input': 0.00015, 'output': 0.0006},
    'gpt-4-turbo': {'input': 0.01, 'output': 0.03},
    'gpt-3.5-turbo': {'input': 0.0005, 'output': 0.0015},
    
    # Claude / Anthropic
    'claude-3-5-sonnet': {'input': 0.003, 'output': 0.015},
    'claude-3-opus': {'input': 0.015, 'output': 0.075},
    'claude-3-haiku': {'input': 0.00025, 'output': 0.00125},
    
    # Gemini / Google
    'gemini-1.5-pro': {'input': 0.00125, 'output': 0.005},
    'gemini-1.5-flash': {'input': 0.000075, 'output': 0.0003},
    'gemini-2.0-flash': {'input': 0.0001, 'output': 0.0004},
    
    # 默认价格 (未知模型)
    'default': {'input': 0.001, 'output': 0.003}
}

def calculate_cost(model_name: str, input_tokens: int, output_tokens: int) -> float:
    """
    计算 LLM 调用费用
    
    Args:
        model_name: 模型名称
        input_tokens: 输入 token 数
        output_tokens: 输出 token 数
    
    Returns:
        费用 (USD)
    """
    # 提取模型名称（去掉提供商前缀）
    model_key = model_name.lower()
    if '/' in model_key:
        model_key = model_key.split('/')[-1]
    
    # 获取价格
    price = MODEL_PRICES.get(model_key, MODEL_PRICES['default'])
    
    # 计算费用 (价格是每 1K tokens)
    input_cost = (input_tokens / 1000) * price['input']
    output_cost = (output_tokens / 1000) * price['output']
    
    return round(input_cost + output_cost, 6)

def record_token_usage(provider: str, model: str, prompt_tokens: int, 
                       completion_tokens: int, cost_usd: float = None):
    """
    记录 LLM 调用的 token 使用和费用到 token_usage 表
    
    Args:
        provider: 提供商名称 (如 'moonshot', 'aliyun')
        model: 模型名称 (如 'kimi-k2.5', 'qwen3.5-plus')
        prompt_tokens: 输入 token 数
        completion_tokens: 输出 token 数
        cost_usd: 费用 (USD)，如果不提供则自动计算
    """
    try:
        total_tokens = prompt_tokens + completion_tokens
        
        # 如果没有提供费用，自动计算
        if cost_usd is None:
            cost_usd = calculate_cost(model, prompt_tokens, completion_tokens)
        
        conn = get_db()
        c = conn.cursor()
        c.execute(\'\'\'
            INSERT INTO token_usage (timestamp, provider, model, prompt_tokens, 
                                    completion_tokens, total_tokens, cost_usd)
            VALUES (datetime('now'), ?, ?, ?, ?, ?, ?)
        \'\'\', (provider, model, prompt_tokens, completion_tokens, total_tokens, cost_usd))
        conn.commit()
        conn.close()
        logger.info(f"📊 记录 token 使用：{model} - {total_tokens} tokens, ${cost_usd:.6f}")
    except Exception as e:
        logger.error(f"❌ 记录 token 使用失败：{e}")

'''

# 在 login_required 函数之前插入
insert_marker = 'def login_required(f):'
if insert_marker in content:
    content = content.replace(insert_marker, llm_utils_code + insert_marker)
    print("✅ 已插入 LLM 费用记录工具函数")
else:
    print("❌ 未找到插入位置")
    sys.exit(1)

# 保存
with open(app_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ app.py 已更新")
