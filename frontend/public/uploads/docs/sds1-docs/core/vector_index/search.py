"""Files/ 目录向量检索

基于关键词匹配 + 语义相似度的混合检索
"""
import json
import re
from pathlib import Path
from typing import List, Dict, Optional
from difflib import SequenceMatcher
import logging

logger = logging.getLogger('sds.vector_index')

WORKSPACE_ROOT = Path("/Users/mettlyz/.openclaw/workspace")
INDEX_DIR = WORKSPACE_ROOT / 'data' / 'vector-index'

def search_documents(
    query: str,
    top_k: int = 5,
    category_filter: Optional[str] = None
) -> List[Dict]:
    """在 Files/ 索引中搜索相关文档
    
    Args:
        query: 搜索查询
        top_k: 返回结果数
        category_filter: 按分类过滤 (projects/knowledge/literature/etc.)
    
    Returns:
        相关文档块列表，按相关性排序
    """
    chunks_file = INDEX_DIR / 'chunks.json'
    
    if not chunks_file.exists():
        logger.warning("向量索引不存在，请先 build_index()")
        return []
    
    try:
        with open(chunks_file, 'r') as f:
            all_chunks = json.load(f)
    except Exception as e:
        logger.error(f"加载索引失败: {e}")
        return []
    
    # 预处理查询
    query_lower = query.lower()
    query_words = set(re.findall(r'\b\w+\b', query_lower))
    
    # 计算每个 chunk 的相关性得分
    scored_chunks = []
    
    for chunk in all_chunks:
        text = chunk.get('text', '').lower()
        filepath = chunk.get('filepath', '').lower()
        
        # 分类过滤
        if category_filter:
            from .indexer import VectorIndexer
            idx = VectorIndexer()
            cat = idx._detect_category(WORKSPACE_ROOT / chunk['filepath'])
            if cat != category_filter:
                continue
        
        # 1. 关键词匹配得分
        keyword_score = 0
        for word in query_words:
            if word in text:
                keyword_score += 1.0
            if word in filepath:
                keyword_score += 0.5
        
        # 2. 短语匹配得分（更精确）
        phrase_score = 0
        if query_lower in text:
            phrase_score = 3.0
        
        # 3. 语义相似度（基于字符级 n-gram）
        similarity = SequenceMatcher(None, query_lower, text[:500]).ratio()
        
        # 综合得分
        total_score = keyword_score + phrase_score + similarity * 2
        
        if total_score > 0.5:  # 过滤低分
            scored_chunks.append({
                **chunk,
                'score': round(total_score, 3)
            })
    
    # 排序并返回 top_k
    scored_chunks.sort(key=lambda x: x['score'], reverse=True)
    results = scored_chunks[:top_k]
    
    logger.info(f"搜索 '{query[:30]}...' 返回 {len(results)} 个结果")
    return results

def get_knowledge_context(query: str, max_chars: int = 3000) -> str:
    """获取知识上下文，用于注入 LLM prompt
    
    Args:
        query: 任务/主题查询
        max_chars: 最大返回字符数
    
    Returns:
        相关知识文本
    """
    results = search_documents(query, top_k=10)
    
    if not results:
        return ""
    
    contexts = []
    total_chars = 0
    
    for result in results:
        text = result['text']
        filepath = result['filepath']
        score = result['score']
        
        # 截断过长的文本
        display_text = text[:500] if len(text) > 500 else text
        
        context = f"[相关度: {score}] [{filepath}]\n{display_text}\n"
        
        if total_chars + len(context) > max_chars:
            break
        
        contexts.append(context)
        total_chars += len(context)
    
    header = f"=== 相关知识检索 ({len(contexts)} 条) ===\n"
    return header + "\n".join(contexts)

def get_file_summary(filepath: str) -> Optional[Dict]:
    """获取单个文件的摘要信息"""
    full_path = WORKSPACE_ROOT / filepath
    
    if not full_path.exists():
        return None
    
    try:
        text = full_path.read_text(encoding='utf-8', errors='ignore')
        
        # 提取标题（第一行或前50字符）
        lines = text.strip().split('\n')
        title = lines[0][:50] if lines else filepath
        
        # 提取摘要（前200字符）
        summary = text[:200].replace('\n', ' ')
        
        return {
            'filepath': filepath,
            'title': title,
            'summary': summary,
            'size': len(text),
            'lines': len(lines)
        }
    except Exception as e:
        logger.warning(f"读取文件摘要失败 {filepath}: {e}")
        return None
