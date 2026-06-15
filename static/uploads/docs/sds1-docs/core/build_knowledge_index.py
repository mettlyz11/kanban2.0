#!/usr/bin/env python3
"""
Phase 1: Obsidian wiki/ 知识图谱索引
- 扫描所有 .md 文件（排除 archive/）
- 提取内容、清理、分 chunk
- 构建 BM25 关键词索引
- 生成 embedding 向量（BAAI/bge-small-zh-v1.5）
- 构建 FAISS 向量索引
- 输出到 data/knowledge-index/
"""

import os
import sys
import json
import re
import hashlib
import time
from pathlib import Path
from datetime import datetime

# ─── 配置 ───
WIKI_ROOT = Path.home() / '.openclaw' / 'workspace' / 'Files' / 'mettlyzObsidianVault' / 'wiki'
OUTPUT_DIR = Path.home() / '.openclaw' / 'workspace' / 'data' / 'knowledge-index'
EXCLUDE_DIRS = {'archive', '.obsidian'}
MAX_CHUNK_SIZE = 500  # 每个 chunk 最大字数

sys.path.insert(0, str(Path.home() / '.openclaw' / 'workspace'))

def extract_text_from_md(filepath: Path) -> str:
    """从 markdown 提取纯文本"""
    try:
        content = filepath.read_text(encoding='utf-8').strip()
        if not content:
            return ''
        # 去除 frontmatter
        content = re.sub(r'^---\n.*?\n---\n', '', content, flags=re.DOTALL)
        # 去除 markdown 语法但保留语义
        content = re.sub(r'!\[.*?\]\(.*?\)', '', content)  # 图片
        content = re.sub(r'\[(.*?)\]\(.*?\)', r'\1', content)  # 链接 → 纯文本
        content = re.sub(r'[#*~_`>\[\]|]', '', content)  # 语法符号
        # 压缩空行
        content = re.sub(r'\n{3,}', '\n\n', content)
        return content.strip()
    except Exception as e:
        # print(f"  ⚠️ 读取失败 {filepath.name}: {e}")
        return ''

def chunk_text(text: str, filepath: Path) -> list:
    """将文本切分为 chunks"""
    if not text:
        return []
    
    # 用 wiki/ 下的第一级目录作为 category
    try:
        rel = filepath.relative_to(WIKI_ROOT)
        parts = rel.parts
        if len(parts) > 1:
            category = parts[0]
        else:
            category = 'root'
    except:
        category = 'unknown'
    
    if len(text) <= MAX_CHUNK_SIZE:
        return [{
            'content': text,
            'title': filepath.stem,
            'category': category,
            'sub_category': filepath.parent.name if category != 'root' else 'root',
            'filepath': str(filepath.relative_to(WIKI_ROOT.parent.parent.parent)),
            'chunk_id': 0,
            'total_chunks': 1,
            'word_count': len(text)
        }]
    
    # 按段落切分
    paragraphs = text.split('\n\n')
    chunks = []
    current = ''
    
    for p in paragraphs:
        if len(current) + len(p) > MAX_CHUNK_SIZE and current:
            chunks.append(current.strip())
            current = p
        else:
            current = (current + '\n\n' + p).strip()
    
    if current:
        chunks.append(current.strip())
    
    return [{
        'content': c,
        'title': filepath.stem,
        'category': category,
        'sub_category': filepath.parent.name if category != 'root' else 'root',
        'filepath': str(filepath.relative_to(WIKI_ROOT.parent.parent.parent)),
        'chunk_id': i,
        'total_chunks': len(chunks),
        'word_count': len(c)
    } for i, c in enumerate(chunks)]

def scan_wiki():
    """扫描所有 wiki/ 文件"""
    # print("📂 扫描 wiki/ 目录...")
    all_chunks = []
    file_stats = {}
    
    for dirpath, dirnames, filenames in os.walk(WIKI_ROOT):
        # 排除目录
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        
        for fn in filenames:
            if not fn.endswith('.md'):
                continue
            
            filepath = Path(dirpath) / fn
            text = extract_text_from_md(filepath)
            
            if not text:
                continue
            
            # 统计（用 wiki/ 下的第一级目录作为 category）
            try:
                rel = filepath.relative_to(WIKI_ROOT)
                parts = rel.parts
                category = parts[0] if len(parts) > 1 else 'root'
            except:
                category = 'unknown'
            if category not in file_stats:
                file_stats[category] = {'count': 0, 'total_words': 0, 'empty': 0}
            file_stats[category]['count'] += 1
            file_stats[category]['total_words'] += len(text)
            
            chunks = chunk_text(text, filepath)
            all_chunks.extend(chunks)
    
    # print(f"  📊 扫描完成：{sum(s['count'] for s in file_stats.values())} 个文件")
    # print(f"  📝 总 chunk 数：{len(all_chunks)}")
    # print(f"  📈 分类统计：")
    for cat, stats in sorted(file_stats.items(), key=lambda x: -x[1]['count']):
        # print(f"     {cat:15s} → {stats['count']:4d} 文件, {stats['total_words']:6d} 字")
    
    return all_chunks, file_stats

def build_bm25_index(chunks: list):
    """构建 BM25 关键词索引"""
    # print("\n🔤 构建 BM25 关键词索引...")
    
    from rank_bm25 import BM25Okapi
    import jieba
    
    # 中文分词
    texts = []
    for c in chunks:
        tokens = list(jieba.cut(c['content']))
        texts.append(tokens)
    
    bm25 = BM25Okapi(texts)
    # print(f"  ✅ BM25 索引构建完成（{len(texts)} 个文档）")
    return bm25, texts

def build_faiss_index(chunks: list):
    """构建 FAISS 向量索引"""
    # print("\n🧠 构建 FAISS 向量索引...")
    # print("  ⏳ 加载 embedding 模型 (BAAI/bge-small-zh-v1.5)...")
    
    from sentence_transformers import SentenceTransformer
    import numpy as np
    import faiss
    
    model = SentenceTransformer('BAAI/bge-small-zh-v1.5')
    # print(f"  ✅ 模型加载完成，维度={model.get_sentence_embedding_dimension()}")
    
    dim = model.get_sentence_embedding_dimension()
    
    # 分批编码（避免内存爆炸）
    batch_size = 64
    embeddings = []
    
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i+batch_size]
        texts = [c['content'] for c in batch]
        batch_emb = model.encode(texts, show_progress_bar=False, normalize_embeddings=True)
        embeddings.append(batch_emb)
        if (i // batch_size) % 10 == 0:
            # print(f"  编码进度：{min(i+batch_size, len(chunks))}/{len(chunks)}")
    
    all_embeddings = np.vstack(embeddings).astype('float32')
    
    # 构建 FAISS 索引（内积，因为已 normalize）
    index = faiss.IndexFlatIP(dim)
    index.add(all_embeddings)
    
    # print(f"  ✅ FAISS 索引构建完成（{index.ntotal} 个向量，维度={dim}）")
    return index, all_embeddings, model

def save_index(chunks, bm25, bm25_texts, faiss_index, embeddings, model, file_stats):
    """保存所有索引"""
    # print("\n💾 保存索引...")
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # 1. 保存 chunks 元数据
    metadata = []
    for c in chunks:
        metadata.append({
            'content': c['content'],  # 保留原文用于展示
            'title': c['title'],
            'category': c['category'],
            'filepath': c['filepath'],
            'chunk_id': c['chunk_id'],
            'total_chunks': c['total_chunks'],
            'word_count': c['word_count']
        })
    
    with open(OUTPUT_DIR / 'metadata.json', 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    # print(f"  ✅ metadata.json ({len(metadata)} 条)")
    
    # 2. 保存 BM25 分词数据
    with open(OUTPUT_DIR / 'bm25_corpus.json', 'w', encoding='utf-8') as f:
        json.dump(bm25_texts, f, ensure_ascii=False)
    # print(f"  ✅ bm25_corpus.json")
    
    # 3. 保存 FAISS 索引
    import faiss
    faiss.write_index(faiss_index, str(OUTPUT_DIR / 'faiss_index.bin'))
    # print(f"  ✅ faiss_index.bin ({faiss_index.ntotal} 向量)")
    
    # 4. 保存 entities 快速查询索引
    entities = [c for c in chunks if c['category'] == 'entities']
    entities_index = {}
    for e in entities:
        key = e['title'].lower()
        if key not in entities_index:
            entities_index[key] = {
                'title': e['title'],
                'content': e['content'][:200],  # 摘要
                'filepath': e['filepath'],
                'category': e['category']
            }
    
    with open(OUTPUT_DIR / 'entities_index.json', 'w', encoding='utf-8') as f:
        json.dump(entities_index, f, ensure_ascii=False, indent=2)
    # print(f"  ✅ entities_index.json ({len(entities_index)} 实体)")
    
    # 5. 保存 projects 快速查询索引
    projects = [c for c in chunks if c['category'] == 'projects']
    projects_index = {}
    for p in projects:
        key = p['title'].lower()
        if key not in projects_index:
            projects_index[key] = {
                'title': p['title'],
                'content': p['content'][:500],
                'filepath': p['filepath'],
                'category': p['category']
            }
    
    with open(OUTPUT_DIR / 'projects_index.json', 'w', encoding='utf-8') as f:
        json.dump(projects_index, f, ensure_ascii=False, indent=2)
    # print(f"  ✅ projects_index.json ({len(projects_index)} 项目)")
    
    # 6. 保存索引摘要
    summary = {
        'created_at': datetime.now().isoformat(),
        'wiki_root': str(WIKI_ROOT),
        'total_files': sum(s['count'] for s in file_stats.values()),
        'total_chunks': len(chunks),
        'total_words': sum(s['total_words'] for s in file_stats.values()),
        'categories': {k: v['count'] for k, v in file_stats.items()},
        'embedding_model': 'BAAI/bge-small-zh-v1.5',
        'embedding_dim': model.get_sentence_embedding_dimension(),
        'bm25_documents': len(bm25_texts),
        'faiss_vectors': faiss_index.ntotal,
        'files': {
            'metadata': 'metadata.json',
            'bm25_corpus': 'bm25_corpus.json',
            'faiss_index': 'faiss_index.bin',
            'entities_index': 'entities_index.json',
            'projects_index': 'projects_index.json'
        }
    }
    
    with open(OUTPUT_DIR / 'index_summary.json', 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    # print(f"  ✅ index_summary.json")

def main():
    start = time.time()
    # print("=" * 60)
    # print("🚀 Phase 1: Obsidian wiki/ 知识图谱索引")
    # print("=" * 60)
    
    # 1. 扫描
    chunks, file_stats = scan_wiki()
    
    if not chunks:
        # print("❌ 没有找到任何内容！")
        return
    
    # 2. BM25
    bm25, bm25_texts = build_bm25_index(chunks)
    
    # 3. FAISS
    faiss_index, embeddings, model = build_faiss_index(chunks)
    
    # 4. 保存
    save_index(chunks, bm25, bm25_texts, faiss_index, embeddings, model, file_stats)
    
    elapsed = time.time() - start
    # print(f"\n{'=' * 60}")
    # print(f"✅ Phase 1 完成！耗时 {elapsed:.1f} 秒")
    # print(f"   索引位置: {OUTPUT_DIR}")
    # print(f"   文件数: {len(list(OUTPUT_DIR.glob('*')))}")
    # print(f"   总大小: {sum(f.stat().st_size for f in OUTPUT_DIR.iterdir()) / 1024 / 1024:.1f} MB")
    # print(f"{'=' * 60}")

if __name__ == '__main__':
    main()
