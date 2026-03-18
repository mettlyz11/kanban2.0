#!/usr/bin/env python3
"""
同步所有LLM配置到看板数据库
"""

import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.expanduser('~/.openclaw/workspace/kanban/kanban_v5.db')

# 所有已配置的模型列表
ALL_MODELS = [
    # ===== 阿里云通用模型 (11个) =====
    {
        "provider": "aliyun",
        "name": "Qwen Max",
        "model_name": "qwen-max",
        "temperature": 0.7,
        "max_tokens": 8192,
        "context_window": 32000,
        "model_type": "general",
        "supports_vision": 1,
        "supports_reasoning": 1,
        "description": "阿里云Qwen Max旗舰模型，32K上下文，支持多模态和推理"
    },
    {
        "provider": "aliyun",
        "name": "Qwen Plus",
        "model_name": "qwen-plus",
        "temperature": 0.7,
        "max_tokens": 4096,
        "context_window": 128000,
        "model_type": "general",
        "supports_vision": 1,
        "supports_reasoning": 0,
        "description": "阿里云Qwen Plus，128K上下文，平衡性能与成本"
    },
    {
        "provider": "aliyun",
        "name": "Qwen Turbo",
        "model_name": "qwen-turbo",
        "temperature": 0.7,
        "max_tokens": 4096,
        "context_window": 128000,
        "model_type": "general",
        "supports_vision": 0,
        "supports_reasoning": 0,
        "description": "阿里云Qwen Turbo，快速响应，128K上下文"
    },
    {
        "provider": "aliyun",
        "name": "Qwen Coder Plus",
        "model_name": "qwen-coder-plus",
        "temperature": 0.3,
        "max_tokens": 8192,
        "context_window": 131072,
        "model_type": "coding",
        "supports_vision": 1,
        "supports_reasoning": 0,
        "description": "编程专用模型，128K上下文，适合代码生成"
    },
    {
        "provider": "aliyun",
        "name": "Qwen VL Max",
        "model_name": "qwen-vl-max",
        "temperature": 0.7,
        "max_tokens": 4096,
        "context_window": 32000,
        "model_type": "vision",
        "supports_vision": 1,
        "supports_reasoning": 0,
        "description": "视觉理解模型，32K上下文，强大的图像理解能力"
    },
    {
        "provider": "aliyun",
        "name": "Qwen VL Plus",
        "model_name": "qwen-vl-plus",
        "temperature": 0.7,
        "max_tokens": 4096,
        "context_window": 32000,
        "model_type": "vision",
        "supports_vision": 1,
        "supports_reasoning": 0,
        "description": "视觉理解模型Plus版，32K上下文"
    },
    {
        "provider": "aliyun",
        "name": "Qwen Audio",
        "model_name": "qwen-audio",
        "temperature": 0.7,
        "max_tokens": 4096,
        "context_window": 32000,
        "model_type": "audio",
        "supports_vision": 0,
        "supports_reasoning": 0,
        "description": "音频理解模型，支持语音输入和理解"
    },
    {
        "provider": "aliyun",
        "name": "Qwen Math",
        "model_name": "qwen-math",
        "temperature": 0.3,
        "max_tokens": 4096,
        "context_window": 32000,
        "model_type": "math",
        "supports_vision": 0,
        "supports_reasoning": 1,
        "description": "数学推理模型，专门优化数学问题解决"
    },
    {
        "provider": "aliyun",
        "name": "Qwen Long",
        "model_name": "qwen-long",
        "temperature": 0.7,
        "max_tokens": 4096,
        "context_window": 1000000,
        "model_type": "general",
        "supports_vision": 0,
        "supports_reasoning": 0,
        "description": "超长上下文模型，支持百万token上下文"
    },
    {
        "provider": "aliyun",
        "name": "Qwen MoE",
        "model_name": "qwen-moe",
        "temperature": 0.7,
        "max_tokens": 4096,
        "context_window": 32000,
        "model_type": "general",
        "supports_vision": 0,
        "supports_reasoning": 1,
        "description": "混合专家模型，高效推理"
    },
    {
        "provider": "aliyun",
        "name": "Qwen 2.5 72B",
        "model_name": "qwen2.5-72b-instruct",
        "temperature": 0.7,
        "max_tokens": 4096,
        "context_window": 128000,
        "model_type": "general",
        "supports_vision": 0,
        "supports_reasoning": 1,
        "description": "Qwen2.5 72B指令模型，开源模型API版"
    },

    # ===== 阿里云Coding Plan (8个) =====
    {
        "provider": "aliyun-coding",
        "name": "Qwen 3.5 Plus (Coding)",
        "model_name": "qwen3.5-plus",
        "temperature": 0.3,
        "max_tokens": 8192,
        "context_window": 128000,
        "model_type": "coding",
        "supports_vision": 1,
        "supports_reasoning": 1,
        "description": "Coding Plan主模型，代码优化专用，更便宜"
    },
    {
        "provider": "aliyun-coding",
        "name": "MiniMax M2.5",
        "model_name": "MiniMax-M2.5",
        "temperature": 0.3,
        "max_tokens": 4096,
        "context_window": 32000,
        "model_type": "coding",
        "supports_vision": 0,
        "supports_reasoning": 0,
        "description": "MiniMax多语言支持模型"
    },
    {
        "provider": "aliyun-coding",
        "name": "Qwen 3 Coder Plus",
        "model_name": "qwen3-coder-plus",
        "temperature": 0.3,
        "max_tokens": 8192,
        "context_window": 131072,
        "model_type": "coding",
        "supports_vision": 1,
        "supports_reasoning": 0,
        "description": "代码生成增强版"
    },
    {
        "provider": "aliyun-coding",
        "name": "Qwen 3 Coder Next",
        "model_name": "qwen3-coder-next",
        "temperature": 0.3,
        "max_tokens": 8192,
        "context_window": 131072,
        "model_type": "coding",
        "supports_vision": 1,
        "supports_reasoning": 1,
        "description": "下一代代码模型"
    },
    {
        "provider": "aliyun-coding",
        "name": "Qwen 3 Max (2026-01-23)",
        "model_name": "qwen3-max-2026-01-23",
        "temperature": 0.3,
        "max_tokens": 8192,
        "context_window": 32000,
        "model_type": "coding",
        "supports_vision": 1,
        "supports_reasoning": 1,
        "description": "最新max版本，2026年1月发布"
    },
    {
        "provider": "aliyun-coding",
        "name": "GLM-5",
        "model_name": "glm-5",
        "temperature": 0.3,
        "max_tokens": 4096,
        "context_window": 32000,
        "model_type": "coding",
        "supports_vision": 0,
        "supports_reasoning": 1,
        "description": "智谱新一代GLM模型"
    },
    {
        "provider": "aliyun-coding",
        "name": "GLM-4.7",
        "model_name": "glm-4.7",
        "temperature": 0.3,
        "max_tokens": 4096,
        "context_window": 32000,
        "model_type": "coding",
        "supports_vision": 0,
        "supports_reasoning": 1,
        "description": "GLM优化版"
    },
    {
        "provider": "aliyun-coding",
        "name": "Kimi K2.5 (Coding)",
        "model_name": "kimi-k2.5",
        "temperature": 0.3,
        "max_tokens": 8192,
        "context_window": 256000,
        "model_type": "coding",
        "supports_vision": 0,
        "supports_reasoning": 1,
        "description": "Moonshot Kimi系列Coding Plan版"
    },

    # ===== OpenRouter模型 =====
    {
        "provider": "openrouter",
        "name": "Claude 3.5 Sonnet",
        "model_name": "anthropic/claude-3.5-sonnet",
        "temperature": 0.7,
        "max_tokens": 8192,
        "context_window": 200000,
        "model_type": "general",
        "supports_vision": 1,
        "supports_reasoning": 1,
        "description": "Anthropic Claude 3.5 Sonnet，200K上下文"
    },
    {
        "provider": "openrouter",
        "name": "GPT-4o",
        "model_name": "openai/gpt-4o",
        "temperature": 0.7,
        "max_tokens": 4096,
        "context_window": 128000,
        "model_type": "general",
        "supports_vision": 1,
        "supports_reasoning": 0,
        "description": "OpenAI GPT-4o，128K上下文"
    },
    {
        "provider": "openrouter",
        "name": "Gemini 2.0 Flash",
        "model_name": "google/gemini-2.0-flash-exp:free",
        "temperature": 0.7,
        "max_tokens": 8192,
        "context_window": 1000000,
        "model_type": "general",
        "supports_vision": 1,
        "supports_reasoning": 0,
        "description": "Google Gemini 2.0 Flash，免费版，1M上下文"
    },

    # ===== DMXAPI模型 =====
    {
        "provider": "dmxapi",
        "name": "GPT-4o (DMXAPI)",
        "model_name": "gpt-4o",
        "temperature": 0.7,
        "max_tokens": 4096,
        "context_window": 128000,
        "model_type": "general",
        "supports_vision": 1,
        "supports_reasoning": 0,
        "description": "DMXAPI平台GPT-4o"
    },
    {
        "provider": "dmxapi",
        "name": "Claude 3.5 Sonnet (DMXAPI)",
        "model_name": "claude-3-5-sonnet-20241022",
        "temperature": 0.7,
        "max_tokens": 8192,
        "context_window": 200000,
        "model_type": "general",
        "supports_vision": 1,
        "supports_reasoning": 1,
        "description": "DMXAPI平台Claude 3.5 Sonnet"
    },
    {
        "provider": "dmxapi",
        "name": "Gemini 1.5 Pro (DMXAPI)",
        "model_name": "gemini-1.5-pro-latest",
        "temperature": 0.7,
        "max_tokens": 8192,
        "context_window": 2000000,
        "model_type": "general",
        "supports_vision": 1,
        "supports_reasoning": 0,
        "description": "DMXAPI平台Gemini 1.5 Pro，2M上下文"
    },
    {
        "provider": "dmxapi",
        "name": "DeepSeek Chat (DMXAPI)",
        "model_name": "deepseek-chat",
        "temperature": 0.7,
        "max_tokens": 4096,
        "context_window": 64000,
        "model_type": "general",
        "supports_vision": 0,
        "supports_reasoning": 1,
        "description": "DMXAPI平台DeepSeek Chat"
    },
    {
        "provider": "dmxapi",
        "name": "Qwen Max (DMXAPI)",
        "model_name": "qwen-max-2024-09-19",
        "temperature": 0.7,
        "max_tokens": 4096,
        "context_window": 32000,
        "model_type": "general",
        "supports_vision": 1,
        "supports_reasoning": 1,
        "description": "DMXAPI平台Qwen Max"
    },
    {
        "provider": "dmxapi",
        "name": "Qwen Coder Plus (DMXAPI)",
        "model_name": "qwen-coder-plus-0828",
        "temperature": 0.3,
        "max_tokens": 8192,
        "context_window": 131072,
        "model_type": "coding",
        "supports_vision": 1,
        "supports_reasoning": 0,
        "description": "DMXAPI平台Qwen Coder Plus"
    },
    {
        "provider": "dmxapi",
        "name": "Llama 3.1 405B (DMXAPI)",
        "model_name": "llama-3.1-405b",
        "temperature": 0.7,
        "max_tokens": 4096,
        "context_window": 128000,
        "model_type": "general",
        "supports_vision": 0,
        "supports_reasoning": 1,
        "description": "DMXAPI平台Llama 3.1 405B开源模型"
    },
    {
        "provider": "dmxapi",
        "name": "Kimi K2 (DMXAPI)",
        "model_name": "kimi-k2",
        "temperature": 0.7,
        "max_tokens": 4096,
        "context_window": 200000,
        "model_type": "general",
        "supports_vision": 0,
        "supports_reasoning": 1,
        "description": "DMXAPI平台Moonshot Kimi K2"
    },
    {
        "provider": "dmxapi",
        "name": "Doubao Pro (DMXAPI)",
        "model_name": "doubao-pro-32k",
        "temperature": 0.7,
        "max_tokens": 4096,
        "context_window": 32000,
        "model_type": "general",
        "supports_vision": 0,
        "supports_reasoning": 0,
        "description": "DMXAPI平台字节跳动豆包Pro"
    },
    {
        "provider": "dmxapi",
        "name": "Yi Large (DMXAPI)",
        "model_name": "yi-large",
        "temperature": 0.7,
        "max_tokens": 4096,
        "context_window": 32000,
        "model_type": "general",
        "supports_vision": 0,
        "supports_reasoning": 1,
        "description": "DMXAPI平台零一万物Yi Large"
    },

    # ===== DeepSeek模型 =====
    {
        "provider": "deepseek",
        "name": "DeepSeek Chat",
        "model_name": "deepseek-chat",
        "temperature": 0.7,
        "max_tokens": 4096,
        "context_window": 64000,
        "model_type": "general",
        "supports_vision": 0,
        "supports_reasoning": 1,
        "description": "DeepSeek官方Chat模型，64K上下文"
    },
    {
        "provider": "deepseek",
        "name": "DeepSeek Coder",
        "model_name": "deepseek-coder",
        "temperature": 0.3,
        "max_tokens": 8192,
        "context_window": 64000,
        "model_type": "coding",
        "supports_vision": 0,
        "supports_reasoning": 1,
        "description": "DeepSeek官方代码模型，专门优化编程任务"
    },

    # ===== Moonshot模型 =====
    {
        "provider": "moonshot",
        "name": "Kimi K2.5",
        "model_name": "kimi-k2.5",
        "temperature": 0.7,
        "max_tokens": 8192,
        "context_window": 256000,
        "model_type": "general",
        "supports_vision": 0,
        "supports_reasoning": 1,
        "description": "Moonshot官方Kimi K2.5，256K长上下文"
    },
    {
        "provider": "moonshot",
        "name": "Kimi K2",
        "model_name": "kimi-k2",
        "temperature": 0.7,
        "max_tokens": 4096,
        "context_window": 200000,
        "model_type": "general",
        "supports_vision": 0,
        "supports_reasoning": 1,
        "description": "Moonshot Kimi K2，200K上下文"
    },
    {
        "provider": "moonshot",
        "name": "Kimi Lite",
        "model_name": "kimi-lite",
        "temperature": 0.7,
        "max_tokens": 4096,
        "context_window": 128000,
        "model_type": "general",
        "supports_vision": 0,
        "supports_reasoning": 0,
        "description": "Moonshot Kimi Lite轻量版，128K上下文"
    },
]


def sync_models():
    """同步所有模型到数据库"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # 获取现有模型 (按provider和model_name去重)
    c.execute('SELECT provider, model_name FROM llm_configs')
    existing = set((row[0], row[1]) for row in c.fetchall())
    
    added = 0
    updated = 0
    skipped = 0
    
    for model in ALL_MODELS:
        key = (model["provider"], model["model_name"])
        
        if key in existing:
            # 更新现有模型信息
            c.execute('''
                UPDATE llm_configs SET
                    name = ?,
                    temperature = ?,
                    max_tokens = ?,
                    context_window = ?,
                    model_type = ?,
                    supports_vision = ?,
                    supports_reasoning = ?,
                    description = ?
                WHERE provider = ? AND model_name = ?
            ''', (
                model["name"],
                model["temperature"],
                model["max_tokens"],
                model["context_window"],
                model["model_type"],
                model["supports_vision"],
                model["supports_reasoning"],
                model["description"],
                model["provider"],
                model["model_name"]
            ))
            updated += 1
        else:
            # 插入新模型
            c.execute('''
                INSERT INTO llm_configs 
                (provider, name, model_name, is_active, is_default, temperature, 
                 max_tokens, context_window, model_type, supports_vision, 
                 supports_reasoning, description, input_cost, output_cost)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                model["provider"],
                model["name"],
                model["model_name"],
                0,  # is_active - 默认不激活
                0,  # is_default
                model["temperature"],
                model["max_tokens"],
                model["context_window"],
                model["model_type"],
                model["supports_vision"],
                model["supports_reasoning"],
                model["description"],
                0.0,  # input_cost
                0.0   # output_cost
            ))
            added += 1
    
    conn.commit()
    conn.close()
    
    print(f"✅ 模型同步完成!")
    print(f"   新增: {added} 个")
    print(f"   更新: {updated} 个")
    print(f"   总计: {len(ALL_MODELS)} 个模型")


if __name__ == '__main__':
    sync_models()
