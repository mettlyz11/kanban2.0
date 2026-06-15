#!/usr/bin/env python3
"""
知识库混合检索模块
- BM25 关键词匹配
- FAISS 向量语义匹配
- 融合排序
- 返回最相关的 Top-K 上下文
"""

import json
import os
from pathlib import Path
from typing import List, Dict, Tuple

INDEX_DIR = Path.home() / '.openclaw' / 'workspace' / 'data' / 'knowledge-index'


class KnowledgeRetriever:
    """知识库混合检索器"""
    
    def __init__(self, index_dir: Path = INDEX_DIR):
        self.index_dir = index_dir
        
        # 加载 metadata
        with open(index_dir / 'metadata.json', encoding='utf-8') as f:
            self.metadata = json.load(f)
        
        # 加载 BM25
        from rank_bm25 import BM25Okapi
        with open(index_dir / 'bm25_corpus.json', encoding='utf-8') as f:
            self.bm25_corpus = json.load(f)
        self.bm25 = BM25Okapi(self.bm25_corpus)
        
        # 加载 FAISS
        import faiss
        self.faiss_index = faiss.read_index(str(index_dir / 'faiss_index.bin'))
        
        # 加载 embedding 模型
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer('BAAI/bge-small-zh-v1.5')
        
        # 加载 entities 索引
        with open(index_dir / 'entities_index.json', encoding='utf-8') as f:
            self.entities_index = json.load(f)
        
        # 加载 projects 索引
        with open(index_dir / 'projects_index.json', encoding='utf-8') as f:
            self.projects_index = json.load(f)
    
    def search_bm25(self, query: str, top_k: int = 10) -> List[Tuple[float, int]]:
        """BM25 关键词搜索"""
        import jieba
        tokens = list(jieba.cut(query))
        scores = self.bm25.get_scores(tokens)
        
        # 取 Top-K
        indexed_scores = [(float(s), i) for i, s in enumerate(scores) if s > 0]
        indexed_scores.sort(reverse=True)
        return indexed_scores[:top_k]
    
    def search_faiss(self, query: str, top_k: int = 10) -> List[Tuple[float, int]]:
        """FAISS 向量语义搜索"""
        import numpy as np
        
        # 编码查询
        q_vec = self.model.encode([query], normalize_embeddings=True).astype('float32')
        
        # 搜索
        scores, indices = self.faiss_index.search(q_vec, top_k)
        
        results = []
        for s, i in zip(scores[0], indices[0]):
            if i >= 0:
                results.append((float(s), int(i)))
        return results
    
    def hybrid_search(self, query: str, top_k: int = 5,
                      bm25_weight: float = 0.4,
                      faiss_weight: float = 0.4,
                      structure_weight: float = 0.2) -> List[Dict]:
        """混合检索：BM25 + FAISS + 结构匹配"""
        
        # BM25 搜索
        bm25_results = self.search_bm25(query, top_k * 2)
        
        # FAISS 搜索
        faiss_results = self.search_faiss(query, top_k * 2)
        
        # 归一化分数
        def normalize(results):
            if not results:
                return {}
            max_score = max(s for s, _ in results)
            if max_score == 0:
                return {}
            return {idx: s / max_score for s, idx in results}
        
        bm25_scores = normalize(bm25_results)
        faiss_scores = normalize(faiss_results)
        
        # 融合所有候选
        all_indices = set(bm25_scores.keys()) | set(faiss_scores.keys())
        
        fused = []
        for idx in all_indices:
            b_score = bm25_scores.get(idx, 0.0)
            f_score = faiss_scores.get(idx, 0.0)
            
            # 结构匹配：同 category 的 boost
            meta = self.metadata[idx] if idx < len(self.metadata) else {}
            structure_boost = 0.1 if meta.get('category') == 'entities' else 0.0
            
            final_score = (
                bm25_weight * b_score +
                faiss_weight * f_score +
                structure_weight * structure_boost
            )
            
            fused.append((final_score, idx))
        
        # 排序取 Top-K
        fused.sort(reverse=True)
        
        # 构建结果
        results = []
        for score, idx in fused[:top_k]:
            if idx < len(self.metadata):
                meta = self.metadata[idx]
                results.append({
                    'score': round(score, 4),
                    'title': meta['title'],
                    'category': meta['category'],
                    'sub_category': meta.get('sub_category', ''),
                    'content': meta['content'],
                    'filepath': meta['filepath'],
                    'chunk_id': meta['chunk_id'],
                    'total_chunks': meta['total_chunks'],
                })
        
        return results
    
    def format_context(self, query: str, top_k: int = 5, max_tokens: int = 2000) -> str:
        """格式化检索结果为 LLM 可读上下文"""
        results = self.hybrid_search(query, top_k)
        
        if not results:
            return ""
        
        parts = [f"【本地知识库参考 - 与\"{query}\"相关的内容】"]
        total_len = len(parts[0])
        
        for i, r in enumerate(results, 1):
            chunk = (
                f"\n--- 参考 {i} ({r['category']}/{r['title']}, 相关度: {r['score']}) ---\n"
                f"{r['content']}"
            )
            
            if total_len + len(chunk) > max_tokens * 2:  # 粗略估计
                break
            
            parts.append(chunk)
            total_len += len(chunk)
        
        return '\n'.join(parts)
    
    def quick_entity_lookup(self, name: str) -> Dict:
        """快速实体查询"""
        key = name.lower()
        if key in self.entities_index:
            return self.entities_index[key]
        return None
    
    def quick_project_lookup(self, name: str) -> Dict:
        """快速项目查询"""
        key = name.lower()
        if key in self.projects_index:
            return self.projects_index[key]
        return None


def main():
    """测试检索效果"""
    import sys
    # print("加载知识库索引...")
    retriever = KnowledgeRetriever()
    # print(f"  已加载 {len(retriever.metadata)} 个文档, {len(retriever.entities_index)} 个实体")
    
    queries = [
        "包头九原区诉讼",
        "T109 过渡态计算",
        "和光智成 融资",
        "深云智合 公司",
        "宋薇 Viva 联系人",
        "北航 自动化实验室",
    ]
    
    for q in queries:
        # print(f"\n{'=' * 60}")
        # print(f"🔍 查询: {q}")
        # print(f"{'=' * 60}")
        
        results = retriever.hybrid_search(q, top_k=3)
        for i, r in enumerate(results, 1):
            # print(f"  {i}. [{r['category']}/{r['title']}] 相关度: {r['score']}")
            # print(f"     {r['content'][:100]}...")
        
        context = retriever.format_context(q, top_k=3)
        # print(f"\n  格式化上下文长度: {len(context)} 字")


if __name__ == '__main__':
    main()
