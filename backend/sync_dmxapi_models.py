#!/usr/bin/env python3
"""
同步 DMXAPI 725个模型到新看板大模型栏
- 读取 DMXAPI 模型列表
- 按厂商分类展示
- 添加模型能力标签
- 保留现有阿里云模型配置
- 新增 DMXAPI 模型作为独立分组
"""

import sqlite3
import json
import os
from datetime import datetime

# 数据库路径
DB_PATH = os.path.expanduser('~/.openclaw/workspace/kanban-react/database/kanban_v5.db')
DMXAPI_MODELS_PATH = '/tmp/dmxapi_models.json'

# 提供商映射（标准化）
PROVIDER_MAPPING = {
    'ali': 'ALI',
    'aliyun': 'ALI',
    'openai': 'OPENAI',
    'custom': 'CUSTOM',
    'midjourney': 'MIDJOURNEY',
    'vertex-ai': 'VERTEX_AI',
    'kling': 'KLING',
    'minimax': 'MINIMAX',
    'zhipu_4v': 'ZHIPU',
    'zhipu': 'ZHIPU',
    'coze': 'COZE',
    'baidu': 'BAIDU',
    'moonshot': 'MOONSHOT',
    'xunfei': 'XUNFEI',
    'lingyiwanwu': 'LINGYI',
    'volcengine': 'VOLCENGINE',
    'tencent': 'TENCENT',
    'suno': 'SUNO',
    'deepseek': 'DEEPSEEK',
    'flux': 'FLUX',
    'xai': 'XAI',
    'jina': 'JINA',
    'siliconflow': 'SILICONFLOW',
    'vidu': 'VIDU',
}

# 模型类型检测规则
MODEL_TYPE_RULES = [
    # 图像生成
    (['image', 'img', 'vision', 'vl', 'multimodal', '4v'], 'vision'),
    # 代码
    (['code', 'coder', 'coding', 'dev', 'programming', 'software'], 'coding'),
    # 音频
    (['audio', 'voice', 'speech', 'sound', 'music', 'suno'], 'audio'),
    # 视频
    (['video', 'vidu', 'kling', 'generate-video'], 'video'),
    # 数学
    (['math', 'math-', 'reasoning', 'think'], 'math'),
    # 嵌入
    (['embed', 'embedding', 'vector'], 'embedding'),
    # 长文本
    (['long', '128k', '256k', '1m', '1000000'], 'long-context'),
]

# 能力标签规则
CAPABILITY_RULES = {
    'chat': ['chat', 'conversation', 'dialogue', 'instruct'],
    'vision': ['vision', 'image', 'vl', '4v', 'multimodal', 'gpt-4o', 'claude-3', 'gemini'],
    'coding': ['code', 'coder', 'coding', 'dev', 'programming', 'software'],
    'audio': ['audio', 'voice', 'speech', 'sound', 'music', 'suno'],
    'video': ['video', 'vidu', 'kling', 'generate-video'],
    'reasoning': ['reasoning', 'think', 'o1', 'o3', 'math', 'logic'],
    'embedding': ['embed', 'embedding', 'vector'],
    'search': ['search', 'retrieve', 'rag', 'perplexity'],
    'image_gen': ['dall-e', 'midjourney', 'mj_', 'flux', 'image-gen'],
}

def detect_model_type(model_id: str, model_name: str = '') -> str:
    """检测模型类型"""
    text = f"{model_id} {model_name}".lower()
    
    for keywords, model_type in MODEL_TYPE_RULES:
        if any(kw in text for kw in keywords):
            return model_type
    
    return 'general'

def detect_capabilities(model_id: str, model_name: str = '') -> list:
    """检测模型能力标签"""
    text = f"{model_id} {model_name}".lower()
    capabilities = []
    
    for cap, keywords in CAPABILITY_RULES.items():
        if any(kw in text for kw in keywords):
            capabilities.append(cap)
    
    # 默认所有模型都支持对话
    if 'chat' not in capabilities:
        capabilities.append('chat')
    
    return capabilities

def get_context_window(model_id: str) -> int:
    """根据模型ID推断上下文窗口"""
    text = model_id.lower()
    
    if '1m' in text or '1000000' in text or 'million' in text:
        return 1000000
    elif '2m' in text or '2000000' in text:
        return 2000000
    elif '256k' in text or '256000' in text:
        return 256000
    elif '200k' in text or '200000' in text:
        return 200000
    elif '128k' in text or '128000' in text:
        return 128000
    elif '131k' in text or '131072' in text:
        return 131072
    elif '32k' in text or '32000' in text:
        return 32000
    elif '64k' in text or '64000' in text:
        return 64000
    elif '16k' in text or '16000' in text:
        return 16000
    elif '8k' in text or '8000' in text:
        return 8000
    elif '4k' in text or '4000' in text:
        return 4000
    
    return 8192  # 默认值

def supports_vision(model_id: str) -> bool:
    """检测是否支持视觉"""
    text = model_id.lower()
    vision_keywords = ['vision', 'vl', '4v', 'multimodal', 'gpt-4o', 'claude-3-opus', 'claude-3-sonnet', 
                       'gemini-1.5', 'gemini-2', 'qwen-vl', 'llava', 'cogvlm']
    return any(kw in text for kw in vision_keywords)

def supports_reasoning(model_id: str) -> bool:
    """检测是否支持推理"""
    text = model_id.lower()
    reasoning_keywords = ['o1', 'o3', 'reasoning', 'think', 'r1', 'deepseek-r', 'qwq']
    return any(kw in text for kw in reasoning_keywords)

def format_model_name(model_id: str, provider: str) -> str:
    """格式化模型显示名称"""
    # 移除常见前缀后缀
    name = model_id.replace('-latest', '').replace('-preview', '').replace('-2024', '').replace('-2025', '')
    
    # 特殊处理
    if 'gpt-4' in name or 'gpt-5' in name:
        return name.upper().replace('-', ' ')
    elif 'claude' in name:
        parts = name.split('-')
        return ' '.join([p.capitalize() for p in parts])
    
    return name.replace('-', ' ').title()

def load_dmxapi_models():
    """加载DMXAPI模型列表"""
    with open(DMXAPI_MODELS_PATH, 'r') as f:
        data = json.load(f)
    return data.get('data', [])

def get_existing_aliyun_models(conn):
    """获取现有的阿里云模型配置"""
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, provider, name, model_name, model_type, supports_vision, supports_reasoning, description "
        "FROM llm_configs WHERE provider IN ('aliyun', 'aliyun-coding')"
    )
    return cursor.fetchall()

def clear_existing_dmxapi_models(conn):
    """清除现有的DMXAPI模型（除了保留的核心模型）"""
    cursor = conn.cursor()
    # 保留核心模型（ID 34-43），删除其他标记为dmxapi的模型
    cursor.execute(
        "DELETE FROM llm_configs WHERE provider = 'dmxapi' AND id > 43"
    )
    conn.commit()
    print(f"已清理现有DMXAPI模型（保留核心10个）")

def insert_dmxapi_models(conn, models):
    """插入DMXAPI模型到数据库"""
    cursor = conn.cursor()
    
    inserted = 0
    skipped = 0
    
    for model in models:
        model_id = model.get('id', '')
        provider_raw = model.get('owned_by', 'custom')
        provider = PROVIDER_MAPPING.get(provider_raw, provider_raw.upper())
        
        # 检测模型属性
        model_type = detect_model_type(model_id)
        capabilities = detect_capabilities(model_id)
        context_window = get_context_window(model_id)
        vision = 1 if supports_vision(model_id) else 0
        reasoning = 1 if supports_reasoning(model_id) else 0
        
        # 格式化名称
        name = format_model_name(model_id, provider)
        
        # 构建描述
        cap_str = ', '.join(capabilities[:3]) if capabilities else 'chat'
        description = f"DMXAPI {provider}模型 | 能力: {cap_str} | 上下文: {context_window//1000}K"
        
        # 检查是否已存在
        cursor.execute(
            "SELECT id FROM llm_configs WHERE model_name = ? AND provider = 'dmxapi'",
            (model_id,)
        )
        if cursor.fetchone():
            skipped += 1
            continue
        
        # 插入新模型
        cursor.execute(
            """INSERT INTO llm_configs 
               (provider, name, model_name, is_active, is_default, temperature, max_tokens, 
                context_window, model_type, supports_vision, supports_reasoning, description)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            ('dmxapi', name, model_id, 0, 0, 0.7, 4096, context_window, 
             model_type, vision, reasoning, description)
        )
        inserted += 1
        
        if inserted % 100 == 0:
            print(f"已插入 {inserted} 个模型...")
    
    conn.commit()
    return inserted, skipped

def main():
    print("=" * 60)
    print("DMXAPI 模型同步工具")
    print("=" * 60)
    
    # 检查模型文件
    if not os.path.exists(DMXAPI_MODELS_PATH):
        print(f"错误: 模型文件不存在 {DMXAPI_MODELS_PATH}")
        return
    
    # 加载DMXAPI模型
    print("\n1. 加载DMXAPI模型列表...")
    models = load_dmxapi_models()
    print(f"   找到 {len(models)} 个模型")
    
    # 统计各厂商数量
    provider_stats = {}
    for m in models:
        p = m.get('owned_by', 'custom')
        provider_stats[p] = provider_stats.get(p, 0) + 1
    
    print("\n2. 厂商分布:")
    for p, count in sorted(provider_stats.items(), key=lambda x: -x[1])[:10]:
        print(f"   {p}: {count} 个模型")
    
    # 连接数据库
    print(f"\n3. 连接数据库...")
    conn = sqlite3.connect(DB_PATH)
    
    # 查看现有阿里云模型
    existing_aliyun = get_existing_aliyun_models(conn)
    print(f"   现有阿里云模型: {len(existing_aliyun)} 个（保留）")
    
    # 清理现有DMXAPI模型
    clear_existing_dmxapi_models(conn)
    
    # 插入新模型
    print(f"\n4. 插入DMXAPI模型...")
    inserted, skipped = insert_dmxapi_models(conn, models)
    print(f"   插入: {inserted} 个")
    print(f"   跳过(重复): {skipped} 个")
    
    # 统计结果
    print(f"\n5. 同步完成!")
    cursor = conn.cursor()
    cursor.execute("SELECT provider, COUNT(*) FROM llm_configs GROUP BY provider ORDER BY COUNT(*) DESC")
    stats = cursor.fetchall()
    print("\n   数据库模型统计:")
    for provider, count in stats:
        print(f"     {provider}: {count} 个")
    
    total = sum(c for _, c in stats)
    print(f"\n   总计: {total} 个模型")
    
    conn.close()
    print("\n" + "=" * 60)

if __name__ == '__main__':
    main()
