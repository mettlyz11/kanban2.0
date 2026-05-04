#!/usr/bin/env python3
"""
Phase 3 完成: 提取剩余 121 篇 PDF 文献并合并到知识库索引
"""

import os
import sys
import json
import time
from pathlib import Path
from datetime import datetime

LITERATURE_DIR = Path.home() / '.openclaw' / 'workspace' / 'Files' / 'YuzhouVault' / '06-文献资料'
OUTPUT_DIR = Path.home() / '.openclaw' / 'workspace' / 'data' / 'knowledge-index'
MAX_CHUNK_SIZE = 500

def extract_text_from_pdf(filepath: Path) -> str:
    """从 PDF 提取文本"""
    try:
        import pdfplumber
        import warnings
        warnings.filterwarnings('ignore')
        with pdfplumber.open(filepath) as pdf:
            text = '\n'.join(page.extract_text() or '' for page in pdf.pages)
        return text.strip()
    except:
        return ''

def chunk_text(text: str, filepath: Path) -> list:
    """将文本切分为 chunks"""
    if not text:
        return []
    
    try:
        rel = filepath.relative_to(LITERATURE_DIR)
        category = f"文献-{rel.parts[0]}" if rel.parts else '文献'
    except:
        category = '文献'
    
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
    
    result = []
    for i, c in enumerate(chunks[:5]):
        result.append({
            'content': c[:MAX_CHUNK_SIZE],
            'title': filepath.stem,
            'category': category,
            'sub_category': filepath.parent.name,
            'filepath': str(filepath),
            'chunk_id': i,
            'total_chunks': min(len(chunks), 5),
            'word_count': min(len(c), MAX_CHUNK_SIZE)
        })
    return result

def main():
    start = time.time()
    print("=" * 60)
    print("🚀 Phase 3 完成: 提取剩余 121 篇 PDF 文献")
    print("=" * 60)
    
    # 加载已有索引
    meta_file = OUTPUT_DIR / 'metadata.json'
    with open(meta_file, encoding='utf-8') as f:
        existing_meta = json.load(f)
    print(f"\n📊 已有索引: {len(existing_meta)} chunks")
    
    # 获取已索引的 PDF
    indexed_pdfs = set()
    for m in existing_meta:
        if m.get('filepath', '').startswith('Files/YuzhouVault'):
            indexed_pdfs.add(m['filepath'])
    print(f"已索引 PDF: {len(indexed_pdfs)} 个")
    
    # 扫描所有 PDF
    all_pdfs = list(LITERATURE_DIR.rglob('*.pdf'))
    print(f"总 PDF 数: {len(all_pdfs)}")
    
    # 过滤出未索引的
    remaining_pdfs = [p for p in all_pdfs if str(p) not in indexed_pdfs]
    print(f"待提取 PDF: {len(remaining_pdfs)}")
    
    # 提取
    new_chunks = []
    success = 0
    failed = 0
    
    for i, pdf in enumerate(remaining_pdfs):
        text = extract_text_from_pdf(pdf)
        if text:
            success += 1
            chunks = chunk_text(text, pdf)
            new_chunks.extend(chunks)
        else:
            failed += 1
        
        if (i + 1) % 20 == 0:
            print(f"  进度: {i+1}/{len(remaining_pdfs)}, 成功: {success}, 失败: {failed}")
    
    print(f"\n✅ 提取完成：成功 {success}，失败 {failed}")
    print(f"  新增 chunks: {len(new_chunks)}")
    
    if not new_chunks:
        print("没有新增内容！")
        return
    
    # 合并到 metadata
    all_meta = existing_meta + new_chunks
    with open(OUTPUT_DIR / 'metadata.json', 'w', encoding='utf-8') as f:
        json.dump(all_meta, f, ensure_ascii=False, indent=2)
    
    # 更新 BM25 语料
    bm25_file = OUTPUT_DIR / 'bm25_corpus.json'
    with open(bm25_file, encoding='utf-8') as f:
        existing_bm25 = json.load(f)
    
    import jieba
    new_bm25 = [list(jieba.cut(c['content'])) for c in new_chunks]
    all_bm25 = existing_bm25 + new_bm25
    with open(bm25_file, 'w', encoding='utf-8') as f:
        json.dump(all_bm25, f, ensure_ascii=False)
    
    # 更新 FAISS 索引
    print("\n🧠 更新 FAISS 向量索引...")
    from sentence_transformers import SentenceTransformer
    import numpy as np
    import faiss
    
    model = SentenceTransformer('BAAI/bge-small-zh-v1.5')
    
    # 编码新 chunks
    batch_size = 64
    new_embeddings = []
    for i in range(0, len(new_chunks), batch_size):
        batch = new_chunks[i:i+batch_size]
        texts = [c['content'] for c in batch]
        emb = model.encode(texts, show_progress_bar=False, normalize_embeddings=True)
        new_embeddings.append(emb)
    all_new_emb = np.vstack(new_embeddings).astype('float32')
    
    # 合并
    existing_emb = np.load(OUTPUT_DIR / 'embeddings.npy')
    all_emb = np.vstack([existing_emb, all_new_emb]).astype('float32')
    
    dim = model.get_sentence_embedding_dimension()
    index = faiss.IndexFlatIP(dim)
    index.add(all_emb)
    faiss.write_index(index, str(OUTPUT_DIR / 'faiss_index.bin'))
    np.save(OUTPUT_DIR / 'embeddings.npy', all_emb)
    
    # 更新摘要
    summary = {
        'created_at': datetime.now().isoformat(),
        'total_files': len(all_meta),
        'total_chunks': len(all_meta),
        'total_words': sum(c.get('word_count', 0) for c in all_meta),
        'embedding_model': 'BAAI/bge-small-zh-v1.5',
        'embedding_dim': dim,
        'bm25_documents': len(all_bm25),
        'faiss_vectors': index.ntotal,
        'sources': {
            'wiki_entities': len([m for m in all_meta if m['category'] in ['entities','concepts','notes','papers','projects','topics','meetings','sources']]),
            'projects': len([m for m in all_meta if m['category'] == 'projects' and not m.get('filepath','').startswith('Files/YuzhouVault')]),
            'literature': len([m for m in all_meta if m.get('filepath','').startswith('Files/YuzhouVault/06-文献')]),
        }
    }
    with open(OUTPUT_DIR / 'index_summary.json', 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    elapsed = time.time() - start
    print(f"\n{'=' * 60}")
    print(f"✅ Phase 3 完成！耗时 {elapsed:.1f} 秒")
    print(f"   总 PDF 索引: {summary['sources']['literature']} 篇")
    print(f"   总 chunks: {len(all_meta)}")
    print(f"   FAISS 向量: {index.ntotal}")
    print(f"{'=' * 60}")

if __name__ == '__main__':
    main()
