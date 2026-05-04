#!/usr/bin/env python3
"""
Phase 5: 重建 Obsidian Vault 完整索引
- 索引整个 Files/mettlyzObsidianVault/ 目录
- 包含: 根级别文档(358KB) + wiki/entities(117KB) + 99-system(573KB)
- 合并 Projects + PDF 文献 → 完整知识库
"""

import os
import sys
import json
import re
import time
from pathlib import Path
from datetime import datetime

VAULT_ROOT = Path.home() / '.openclaw' / 'workspace' / 'Files' / 'mettlyzObsidianVault'
PROJECTS_ROOT = Path.home() / '.openclaw' / 'workspace' / 'Files' / 'Projects'
LITERATURE_DIR = Path.home() / '.openclaw' / 'workspace' / 'Files' / 'YuzhouVault' / '06-文献资料'
OUTPUT_DIR = Path.home() / '.openclaw' / 'workspace' / 'data' / 'knowledge-index'
MAX_CHUNK_SIZE = 600

# 排除模式
EXCLUDE_DIRS = {'.obsidian', '__pycache__', 'node_modules', '.git', 'venv', '.venv'}

def classify_obsidian(filepath: Path) -> tuple:
    """分类 Obsidian 文件"""
    try:
        rel = filepath.relative_to(VAULT_ROOT)
    except:
        return ('unknown', 'unknown')
    parts = rel.parts
    
    # 根级别文件（不在子目录中）
    if len(parts) == 1 and filepath.suffix == '.md':
        return ('vault_docs', 'root_level')
    
    if parts[0] == 'wiki':
        if len(parts) >= 3 and parts[1] == 'entities':
            return ('wiki_entities', parts[2] if len(parts) > 2 else 'entities')
        sub = parts[1] if len(parts) > 1 else 'other'
        return ('wiki_' + sub, sub)
    
    if parts[0] == '99-system':
        sub = parts[2] if len(parts) > 2 else 'other'
        return ('vault_cleanup', sub)
    
    return ('vault_other', parts[0])

def extract_text(filepath: Path) -> str:
    """提取文件文本（过滤空内容和纯模板）"""
    try:
        text = filepath.read_text(encoding='utf-8', errors='ignore').strip()
        if not text:
            return ''
        # 过滤纯 frontmatter 或只有 wikilink 的文件
        lines = [l for l in text.split('\n') if l.strip() 
                 and not l.strip().startswith('---') 
                 and not l.strip().startswith('>')
                 and not (l.strip().startswith('[[') and l.strip().endswith(']]'))]
        meaningful = [l for l in lines if l.strip() and l.strip() not in ['## 相关信息', '- 待补充', '---']]
        if len(meaningful) < 2:
            return ''
        return text
    except:
        return ''

def chunk_text(text: str, filepath: Path, category: str, sub_category: str) -> list:
    """将文本切分为 chunks"""
    if not text:
        return []
    
    # 按 markdown 标题切分
    sections = re.split(r'(?=^#{1,6}\s)', text, flags=re.MULTILINE)
    sections = [s.strip() for s in sections if s.strip()]
    
    chunks = []
    current = ''
    
    for section in sections:
        if len(current) + len(section) > MAX_CHUNK_SIZE and current:
            chunks.append(current.strip())
            current = section
        else:
            current = (current + '\n\n' + section).strip()
    
    if current:
        chunks.append(current.strip())
    
    # 如果整个文件很小
    if not chunks and len(text) <= MAX_CHUNK_SIZE:
        chunks = [text]
    
    result = []
    for i, c in enumerate(chunks):
        result.append({
            'content': c[:MAX_CHUNK_SIZE],
            'title': filepath.stem,
            'category': category,
            'sub_category': sub_category,
            'filepath': str(filepath.relative_to(Path.home() / '.openclaw' / 'workspace')),
            'chunk_id': i,
            'total_chunks': len(chunks),
            'word_count': min(len(c), MAX_CHUNK_SIZE)
        })
    return result

def chunk_project_file(text: str, filepath: Path) -> list:
    """项目文件 chunk"""
    if not text:
        return []
    try:
        rel = filepath.relative_to(PROJECTS_ROOT)
        project_name = rel.parts[0] if rel.parts else 'unknown'
    except:
        project_name = 'unknown'
    
    sections = re.split(r'(?=^#{1,6}\s)', text, flags=re.MULTILINE)
    sections = [s.strip() for s in sections if s.strip()]
    
    chunks = []
    current = ''
    for section in sections:
        if len(current) + len(section) > MAX_CHUNK_SIZE and current:
            chunks.append(current.strip())
            current = section
        else:
            current = (current + '\n\n' + section).strip()
    if current:
        chunks.append(current.strip())
    
    if not chunks and len(text) <= MAX_CHUNK_SIZE:
        chunks = [text]
    
    return [{
        'content': c[:MAX_CHUNK_SIZE],
        'title': filepath.stem,
        'category': 'projects',
        'sub_category': project_name,
        'filepath': str(filepath.relative_to(Path.home() / '.openclaw' / 'workspace')),
        'chunk_id': i,
        'total_chunks': len(chunks),
        'word_count': min(len(c), MAX_CHUNK_SIZE)
    } for i, c in enumerate(chunks)]

def scan_obsidian() -> tuple:
    """扫描 Obsidian Vault"""
    print("\n📂 Phase 5a: 扫描 Obsidian Vault...")
    all_chunks = []
    stats = {}
    empty_count = 0
    
    for dirpath, dirnames, filenames in os.walk(VAULT_ROOT):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        
        for fn in filenames:
            if not fn.endswith('.md'):
                continue
            
            filepath = Path(dirpath) / fn
            text = extract_text(filepath)
            
            if not text:
                empty_count += 1
                continue
            
            category, sub = classify_obsidian(filepath)
            key = f"{category}/{sub}"
            if key not in stats:
                stats[key] = {'count': 0, 'total_words': 0}
            stats[key]['count'] += 1
            stats[key]['total_words'] += len(text)
            
            chunks = chunk_text(text, filepath, category, sub)
            all_chunks.extend(chunks)
    
    print(f"  📊 扫描完成：{sum(s['count'] for s in stats.values())} 个有效文件")
    print(f"  ❌ 空文件跳过：{empty_count}")
    print(f"  📝 总 chunk 数：{len(all_chunks)}")
    print(f"  📈 分类统计：")
    for cat, s in sorted(stats.items(), key=lambda x: -x[1]['count']):
        print(f"     {cat:35s} → {s['count']:5d} 文件, {s['total_words']:8d} 字")
    
    return all_chunks, stats

def scan_projects() -> tuple:
    """扫描项目文件"""
    print("\n📂 Phase 5b: 扫描项目文件...")
    all_chunks = []
    stats = {}
    
    for dirpath, dirnames, filenames in os.walk(PROJECTS_ROOT):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        
        for fn in filenames:
            if not fn.endswith(('.md', '.txt', '.rst')):
                continue
            
            filepath = Path(dirpath) / fn
            try:
                text = filepath.read_text(encoding='utf-8', errors='ignore').strip()
            except:
                continue
            if not text:
                continue
            
            chunks = chunk_project_file(text, filepath)
            all_chunks.extend(chunks)
            
            try:
                rel = filepath.relative_to(PROJECTS_ROOT)
                project = rel.parts[0] if rel.parts else 'unknown'
            except:
                project = 'unknown'
            if project not in stats:
                stats[project] = {'count': 0, 'total_words': 0}
            stats[project]['count'] += 1
            stats[project]['total_words'] += len(text)
    
    print(f"  📊 扫描完成：{sum(s['count'] for s in stats.values())} 个文件")
    print(f"  📝 总 chunk 数：{len(all_chunks)}")
    print(f"  📈 分类统计：")
    for proj, s in sorted(stats.items(), key=lambda x: -x[1]['count']):
        print(f"     {proj:15s} → {s['count']:5d} 文件, {s['total_words']:8d} 字")
    
    return all_chunks, stats

def scan_pdfs() -> list:
    """扫描 PDF 文献"""
    print("\n📂 Phase 5c: 扫描 PDF 文献...")
    pdf_files = list(LITERATURE_DIR.rglob('*.pdf'))
    print(f"  发现 {len(pdf_files)} 个 PDF")
    
    chunks = []
    success = 0
    failed = 0
    
    for i, pdf in enumerate(pdf_files):
        try:
            import pdfplumber
            import warnings
            warnings.filterwarnings('ignore')
            with pdfplumber.open(pdf) as p:
                text = '\n'.join(page.extract_text() or '' for page in p.pages)
            text = text.strip()
        except:
            failed += 1
            continue
        
        if not text:
            failed += 1
            continue
        
        success += 1
        try:
            rel = pdf.relative_to(LITERATURE_DIR)
            category = f"文献-{rel.parts[0]}" if rel.parts else '文献'
        except:
            category = '文献'
        
        paragraphs = text.split('\n\n')
        current = ''
        file_chunks = []
        for p in paragraphs:
            if len(current) + len(p) > MAX_CHUNK_SIZE and current:
                file_chunks.append(current.strip())
                current = p
            else:
                current = (current + '\n\n' + p).strip()
        if current:
            file_chunks.append(current.strip())
        
        for j, c in enumerate(file_chunks[:5]):
            chunks.append({
                'content': c[:MAX_CHUNK_SIZE],
                'title': pdf.stem,
                'category': category,
                'sub_category': pdf.parent.name,
                'filepath': str(pdf.relative_to(Path.home() / '.openclaw' / 'workspace')),
                'chunk_id': j,
                'total_chunks': min(len(file_chunks), 5),
                'word_count': min(len(c), MAX_CHUNK_SIZE)
            })
        
        if (i + 1) % 30 == 0:
            print(f"  进度: {i+1}/{len(pdf_files)}, 成功: {success}, 失败: {failed}")
    
    print(f"  ✅ 提取完成：成功 {success}，失败 {failed}")
    return chunks

def build_faiss_index(chunks: list):
    """构建 FAISS 向量索引"""
    print("\n🧠 构建 FAISS 向量索引...")
    from sentence_transformers import SentenceTransformer
    import numpy as np
    import faiss
    
    model = SentenceTransformer('BAAI/bge-small-zh-v1.5')
    dim = model.get_sentence_embedding_dimension()
    
    batch_size = 64
    embeddings = []
    
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i+batch_size]
        texts = [c['content'] for c in batch]
        batch_emb = model.encode(texts, show_progress_bar=False, normalize_embeddings=True)
        embeddings.append(batch_emb)
        if (i // batch_size) % 20 == 0:
            print(f"  编码进度：{min(i+batch_size, len(chunks))}/{len(chunks)}")
    
    all_embeddings = np.vstack(embeddings).astype('float32')
    index = faiss.IndexFlatIP(dim)
    index.add(all_embeddings)
    
    print(f"  ✅ FAISS 索引构建完成（{index.ntotal} 个向量，维度={dim}）")
    return index, all_embeddings, model

def build_bm25_index(chunks: list):
    """构建 BM25 索引"""
    print("\n🔤 构建 BM25 关键词索引...")
    from rank_bm25 import BM25Okapi
    import jieba
    
    texts = [list(jieba.cut(c['content'])) for c in chunks]
    bm25 = BM25Okapi(texts)
    print(f"  ✅ BM25 索引构建完成（{len(texts)} 个文档）")
    return bm25, texts

def save_index(chunks, bm25_texts, faiss_index, embeddings, model):
    """保存所有索引"""
    print("\n💾 保存索引...")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    # metadata
    with open(OUTPUT_DIR / 'metadata.json', 'w', encoding='utf-8') as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)
    
    # BM25 corpus
    with open(OUTPUT_DIR / 'bm25_corpus.json', 'w', encoding='utf-8') as f:
        json.dump(bm25_texts, f, ensure_ascii=False)
    
    # FAISS
    import faiss
    faiss.write_index(faiss_index, str(OUTPUT_DIR / 'faiss_index.bin'))
    
    # embeddings
    import numpy as np
    np.save(OUTPUT_DIR / 'embeddings.npy', embeddings)
    
    # entities index
    entities = []
    for c in chunks:
        if c['category'] == 'wiki_entities' and c['chunk_id'] == 0:
            entities.append({
                'name': c['title'],
                'category': c['sub_category'],
                'filepath': c['filepath'],
                'word_count': c['word_count']
            })
    with open(OUTPUT_DIR / 'entities_index.json', 'w', encoding='utf-8') as f:
        json.dump(entities, f, ensure_ascii=False, indent=2)
    
    # projects index (空)
    with open(OUTPUT_DIR / 'projects_index.json', 'w', encoding='utf-8') as f:
        json.dump([], f, ensure_ascii=False)
    
    # summary
    sources = {}
    for c in chunks:
        sources[c['category']] = sources.get(c['category'], 0) + 1
    
    summary = {
        'created_at': datetime.now().isoformat(),
        'total_chunks': len(chunks),
        'total_words': sum(c.get('word_count', 0) for c in chunks),
        'embedding_model': 'BAAI/bge-small-zh-v1.5',
        'embedding_dim': model.get_sentence_embedding_dimension(),
        'bm25_documents': len(bm25_texts),
        'faiss_vectors': faiss_index.ntotal,
        'sources': sources,
    }
    with open(OUTPUT_DIR / 'index_summary.json', 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    
    print(f"  ✅ metadata.json ({len(chunks)} 条)")
    print(f"  ✅ bm25_corpus.json ({len(bm25_texts)} 文档)")
    print(f"  ✅ faiss_index.bin ({faiss_index.ntotal} 向量)")
    print(f"  ✅ entities_index.json ({len(entities)} 实体)")

def main():
    start = time.time()
    print("=" * 60)
    print("🚀 Phase 5: Obsidian Vault 完整索引重建")
    print("=" * 60)
    
    # Phase 5a: Obsidian Vault
    obs_chunks, obs_stats = scan_obsidian()
    
    # Phase 5b: 项目文件
    proj_chunks, proj_stats = scan_projects()
    
    # Phase 5c: PDF 文献
    pdf_chunks = scan_pdfs()
    
    # 合并
    all_chunks = obs_chunks + proj_chunks + pdf_chunks
    print(f"\n📊 总合并: {len(all_chunks)} chunks")
    
    if not all_chunks:
        print("❌ 没有找到任何内容！")
        return
    
    # BM25
    bm25, bm25_texts = build_bm25_index(all_chunks)
    
    # FAISS
    faiss_index, embeddings, model = build_faiss_index(all_chunks)
    
    # 保存
    save_index(all_chunks, bm25_texts, faiss_index, embeddings, model)
    
    elapsed = time.time() - start
    print(f"\n{'=' * 60}")
    print(f"✅ Phase 5 完成！耗时 {elapsed:.1f} 秒")
    print(f"   索引位置: {OUTPUT_DIR}")
    print(f"   总 chunk 数: {len(all_chunks)}")
    print(f"{'=' * 60}")

if __name__ == '__main__':
    main()
