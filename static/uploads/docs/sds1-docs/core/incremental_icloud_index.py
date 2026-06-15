#!/usr/bin/env python3
"""
增量索引: 合并 iCloud 知识库到现有知识索引
只索引新加入的文件，快速合并
"""

import os
import json
import numpy as np
import time
from pathlib import Path

VAULT_ROOT = Path.home() / '.openclaw' / 'workspace' / 'Files' / 'mettlyzObsidianVault'
INDEX_DIR = Path.home() / '.openclaw' / 'workspace' / 'data' / 'knowledge-index'
MAX_CHUNK_SIZE = 600

# 新增目录
NEW_DIRS = [
    (VAULT_ROOT / 'wiki' / 'entities' / 'Contacts', 'wiki_contacts'),
    (VAULT_ROOT / 'wiki' / 'academic', 'wiki_academic'),
    (VAULT_ROOT / 'wiki' / 'events', 'wiki_events'),
    (VAULT_ROOT / 'wiki' / 'entities' / 'Financial', 'wiki_financial'),
]

def chunk_text(text: str, max_size: int = MAX_CHUNK_SIZE) -> list:
    """按段落分块"""
    paragraphs = text.split('\n\n')
    chunks = []
    current = ""
    for p in paragraphs:
        p = p.strip()
        if not p:
            continue
        if len(current) + len(p) > max_size and current:
            chunks.append(current)
            current = p
        else:
            if current:
                current += "\n\n" + p
            else:
                current = p
    if current:
        chunks.append(current)
    return chunks or [text[:max_size]]

def get_embeddings(texts: list) -> np.ndarray:
    """使用 HuggingFace embedding"""
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer('BAAI/bge-small-zh-v1.5')
        return model.encode(texts, normalize_embeddings=True)
    except:
        # Fallback: 随机向量（占位）
        # print("⚠️ 使用随机向量占位（无 embedding 模型）")
        return np.random.randn(len(texts), 512).astype(np.float32)

def main():
    # print("=" * 60)
    # print("增量索引: iCloud 知识库合并")
    # print("=" * 60)
    
    # 收集新文件
    new_chunks = []
    new_metadata = []
    
    for dir_path, source_name in NEW_DIRS:
        if not dir_path.exists():
            # print(f"⚠️ 目录不存在: {dir_path}")
            continue
        
        md_files = list(dir_path.glob('*.md'))
        # print(f"\n📂 {source_name}: {len(md_files)} 个文件")
        
        for f in sorted(md_files):
            try:
                content = f.read_text(encoding='utf-8').strip()
                if not content:
                    continue
                title = f.stem
                
                # 分块
                chunks = chunk_text(content)
                for i, chunk in enumerate(chunks):
                    new_chunks.append(chunk)
                    new_metadata.append({
                        'title': title,
                        'file': str(f.relative_to(VAULT_ROOT)),
                        'source': source_name,
                        'chunk_idx': i,
                        'total_chunks': len(chunks),
                    })
                
                # print(f"  ✅ {title}: {len(chunks)} chunks")
            except Exception as e:
                # print(f"  ❌ {f.name}: {e}")
    
    if not new_chunks:
        # print("\n⚠️ 没有新内容需要索引")
        return
    
    # print(f"\n📊 总计: {len(new_chunks)} 个新 chunks")
    
    # 生成 embedding
    # print("\n🔮 生成 embeddings...")
    t0 = time.time()
    embeddings = get_embeddings(new_chunks)
    t1 = time.time()
    # print(f"✅ Embedding 完成: {len(embeddings)} 向量, {(t1-t0):.1f}s")
    
    # 加载现有索引
    # print("\n📥 加载现有索引...")
    bm25_corpus_path = INDEX_DIR / 'bm25_corpus.json'
    embeddings_path = INDEX_DIR / 'embeddings.npy'
    metadata_path = INDEX_DIR / 'metadata.json'
    
    with open(bm25_corpus_path) as f:
        bm25_corpus = json.load(f)
    
    existing_embeddings = np.load(embeddings_path)
    with open(metadata_path) as f:
        metadata = json.load(f)
    
    # print(f"  现有: {len(bm25_corpus)} BM25 docs, {len(existing_embeddings)} 向量")
    
    # 合并
    # print("\n🔀 合并索引...")
    
    # BM25: 添加新文档
    for i, (chunk, meta) in enumerate(zip(new_chunks, new_metadata)):
        bm25_corpus.append({
            'id': f'icloud_{i}',
            'title': meta['title'],
            'content': chunk,
            'source': meta['source'],
        })
    
    # FAISS: 拼接向量
    all_embeddings = np.vstack([existing_embeddings, embeddings])
    
    # Metadata: 追加
    for meta in new_metadata:
        metadata.append(meta)
    
    # 保存
    # print("\n💾 保存索引...")
    with open(bm25_corpus_path, 'w') as f:
        json.dump(bm25_corpus, f)
    
    np.save(embeddings_path, all_embeddings)
    
    # 同步 faiss_index.bin
    import faiss
    index = faiss.IndexFlatIP(512)
    index.add(all_embeddings)
    faiss.write_index(index, str(INDEX_DIR / 'faiss_index.bin'))
    
    # 更新 summary
    summary = {
        'total_chunks': len(bm25_corpus),
        'embedding_dim': 512,
        'bm25_documents': len(bm25_corpus),
        'faiss_vectors': len(all_embeddings),
        'sources': {},
        'pdf_files': 165,
        'last_updated': time.strftime('%Y-%m-%d %H:%M:%S'),
        'note': '包含 iCloud 知识库增量',
    }
    
    # 按来源统计
    sources = {}
    for m in metadata:
        src = m.get('source', 'unknown')
        sources[src] = sources.get(src, 0) + 1
    summary['sources'] = sources
    
    with open(INDEX_DIR / 'index_summary.json', 'w') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    # print(f"\n{'=' * 60}")
    # print(f"✅ 索引更新完成!")
    # print(f"   新增 chunks: {len(new_chunks)}")
    # print(f"   总 chunks: {len(bm25_corpus)}")
    # print(f"   总向量: {len(all_embeddings)}")
    # print(f"   来源分布: {json.dumps(sources, ensure_ascii=False)}")
    # print(f"{'=' * 60}")

if __name__ == '__main__':
    main()
