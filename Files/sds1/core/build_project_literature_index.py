#!/usr/bin/env python3
"""
Phase 2: 项目文件索引 + Phase 3: PDF 文献提取
- Phase 2: 扫描 Files/Projects/ 下的文档文件
- Phase 3: 提取 171 篇 PDF 文献的文本
- 合并到现有知识库索引
"""

import os
import sys
import json
import re
import time
from pathlib import Path
from datetime import datetime

# ─── 配置 ───
PROJECTS_ROOT = Path.home() / '.openclaw' / 'workspace' / 'Files' / 'Projects'
LITERATURE_DIR = Path.home() / '.openclaw' / 'workspace' / 'Files' / 'YuzhouVault' / '06-文献资料'
OUTPUT_DIR = Path.home() / '.openclaw' / 'workspace' / 'data' / 'knowledge-index'
MAX_CHUNK_SIZE = 500
EXCLUDE_DIRS = {'node_modules', 'venv', '.venv', '__pycache__', '.git', 'build', 'dist', '.next', '.cache'}

sys.path.insert(0, str(Path.home() / '.openclaw' / 'workspace'))

def extract_text_from_file(filepath: Path) -> str:
    """从各种文件提取文本"""
    try:
        if filepath.suffix in ('.md', '.txt', '.rst'):
            return filepath.read_text(encoding='utf-8', errors='ignore').strip()
        return ''
    except:
        return ''

def extract_text_from_pdf(filepath: Path) -> str:
    """从 PDF 提取文本"""
    try:
        import pdfplumber
        with pdfplumber.open(filepath) as pdf:
            text = '\n'.join(page.extract_text() or '' for page in pdf.pages)
        return text.strip()
    except Exception as e:
        # 如果 pdfplumber 失败，尝试 PyPDF2
        try:
            from PyPDF2 import PdfReader
            reader = PdfReader(filepath)
            text = '\n'.join(page.extract_text() or '' for page in reader.pages)
            return text.strip()
        except:
            return ''

def chunk_text(text: str, filepath: Path) -> list:
    """将文本切分为 chunks"""
    if not text:
        return []
    
    # 确定分类
    rel = filepath
    parts = rel.parts
    # 查找 "Projects" 后的第一级目录
    project_name = 'unknown'
    for i, p in enumerate(parts):
        if p == 'Projects' and i + 1 < len(parts):
            project_name = parts[i + 1]
            break
        if p == '06-文献资料' and i + 1 < len(parts):
            # 用子目录作为项目名
            project_name = f"文献-{parts[i+1]}" if i + 1 < len(parts) else '文献'
            break
    
    if len(text) <= MAX_CHUNK_SIZE:
        return [{
            'content': text[:MAX_CHUNK_SIZE],
            'title': filepath.stem,
            'category': 'projects',
            'sub_category': project_name,
            'filepath': str(filepath),
            'chunk_id': 0,
            'total_chunks': 1,
            'word_count': min(len(text), MAX_CHUNK_SIZE)
        }]
    
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
        'content': c[:MAX_CHUNK_SIZE],
        'title': filepath.stem,
        'category': 'projects',
        'sub_category': project_name,
        'filepath': str(filepath),
        'chunk_id': i,
        'total_chunks': len(chunks),
        'word_count': min(len(c), MAX_CHUNK_SIZE)
    } for i, c in enumerate(chunks)]

def scan_projects():
    """扫描项目文件"""
    print("\n📂 Phase 2: 扫描项目文件...")
    all_chunks = []
    stats = {}
    
    for dirpath, dirnames, filenames in os.walk(PROJECTS_ROOT):
        # 排除无意义目录
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        
        for fn in filenames:
            if fn.endswith(('.md', '.txt', '.rst')):
                filepath = Path(dirpath) / fn
                text = extract_text_from_file(filepath)
                
                if not text:
                    continue
                
                # 统计
                try:
                    rel = filepath.relative_to(PROJECTS_ROOT)
                    project = rel.parts[0] if rel.parts else 'unknown'
                except:
                    project = 'unknown'
                
                if project not in stats:
                    stats[project] = {'count': 0, 'total_words': 0}
                stats[project]['count'] += 1
                stats[project]['total_words'] += len(text)
                
                chunks = chunk_text(text, filepath)
                all_chunks.extend(chunks)
    
    print(f"  📊 扫描完成：{sum(s['count'] for s in stats.values())} 个文件")
    print(f"  📝 总 chunk 数：{len(all_chunks)}")
    print(f"  📈 分类统计：")
    for proj, s in sorted(stats.items(), key=lambda x: -x[1]['count']):
        print(f"     {proj:15s} → {s['count']:4d} 文件, {s['total_words']:8d} 字")
    
    return all_chunks, stats

def scan_pdfs():
    """扫描 PDF 文献"""
    print("\n📂 Phase 3: 扫描 PDF 文献...")
    
    pdf_files = list(LITERATURE_DIR.rglob('*.pdf'))
    print(f"  发现 {len(pdf_files)} 个 PDF 文件")
    
    # 按子目录分类
    stats = {}
    for pdf in pdf_files:
        try:
            rel = pdf.relative_to(LITERATURE_DIR)
            category = rel.parts[0] if rel.parts else '其他'
        except:
            category = '其他'
        if category not in stats:
            stats[category] = 0
        stats[category] += 1
    
    print(f"  📈 分类统计：")
    for cat, count in sorted(stats.items(), key=lambda x: -x[1]):
        print(f"     {cat:15s} → {count:4d} PDF")
    
    return pdf_files, stats

def extract_pdfs(pdf_files: list, max_pdfs: int = None):
    """提取 PDF 文本"""
    print(f"\n📄 提取 PDF 文本...")
    all_chunks = []
    success = 0
    failed = 0
    
    limit = min(len(pdf_files), max_pdfs) if max_pdfs else len(pdf_files)
    
    for i, pdf in enumerate(pdf_files[:limit]):
        text = extract_text_from_pdf(pdf)
        
        if text:
            success += 1
            # 按段落 chunk
            paragraphs = text.split('\n\n')
            current = ''
            chunks = []
            
            for p in paragraphs:
                if len(current) + len(p) > MAX_CHUNK_SIZE and current:
                    chunks.append(current.strip())
                    current = p
                else:
                    current = (current + '\n\n' + p).strip()
            if current:
                chunks.append(current.strip())
            
            # 确定分类
            try:
                rel = pdf.relative_to(LITERATURE_DIR)
                category = f"文献-{rel.parts[0]}" if rel.parts else '文献'
            except:
                category = '文献'
            
            for j, c in enumerate(chunks[:5]):  # 最多取 5 个 chunk
                all_chunks.append({
                    'content': c[:MAX_CHUNK_SIZE],
                    'title': pdf.stem,
                    'category': category,
                    'sub_category': pdf.parent.name,
                    'filepath': str(pdf),
                    'chunk_id': j,
                    'total_chunks': min(len(chunks), 5),
                    'word_count': min(len(c), MAX_CHUNK_SIZE)
                })
        else:
            failed += 1
        
        if (i + 1) % 20 == 0:
            print(f"  进度: {i+1}/{limit}, 成功: {success}, 失败: {failed}")
    
    print(f"  ✅ 提取完成：成功 {success}，失败 {failed}")
    return all_chunks

def build_faiss_index(chunks: list):
    """构建 FAISS 向量索引"""
    print("\n🧠 构建 FAISS 向量索引...")
    print("  ⏳ 加载 embedding 模型...")
    
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

def merge_with_existing(new_chunks, new_bm25, new_bm25_texts, new_faiss, new_embeddings, model, new_stats):
    """合并到现有索引"""
    print("\n💾 合并索引...")
    
    # 加载现有 metadata
    meta_file = OUTPUT_DIR / 'metadata.json'
    bm25_file = OUTPUT_DIR / 'bm25_corpus.json'
    
    existing_chunks = []
    existing_bm25 = []
    
    if meta_file.exists():
        with open(meta_file, encoding='utf-8') as f:
            existing_chunks = json.load(f)
    if bm25_file.exists():
        with open(bm25_file, encoding='utf-8') as f:
            existing_bm25 = json.load(f)
    
    # 合并
    all_chunks = existing_chunks + new_chunks
    all_bm25 = existing_bm25 + new_bm25_texts
    
    # 重新构建 FAISS
    print("  合并向量...")
    import faiss
    import numpy as np
    
    all_embeddings = np.vstack([np.load(OUTPUT_DIR / 'embeddings.npy'), new_embeddings]).astype('float32') if (OUTPUT_DIR / 'embeddings.npy').exists() else new_embeddings
    
    dim = model.get_sentence_embedding_dimension()
    merged_index = faiss.IndexFlatIP(dim)
    merged_index.add(all_embeddings)
    
    # 保存
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    with open(OUTPUT_DIR / 'metadata.json', 'w', encoding='utf-8') as f:
        json.dump(all_chunks, f, ensure_ascii=False, indent=2)
    
    with open(OUTPUT_DIR / 'bm25_corpus.json', 'w', encoding='utf-8') as f:
        json.dump(all_bm25, f, ensure_ascii=False)
    
    faiss.write_index(merged_index, str(OUTPUT_DIR / 'faiss_index.bin'))
    
    # 保存 embeddings 用于下次合并
    np.save(OUTPUT_DIR / 'embeddings.npy', all_embeddings)
    
    print(f"  ✅ metadata.json ({len(all_chunks)} 条)")
    print(f"  ✅ bm25_corpus.json ({len(all_bm25)} 文档)")
    print(f"  ✅ faiss_index.bin ({merged_index.ntotal} 向量)")
    
    # 更新摘要
    summary = {
        'created_at': datetime.now().isoformat(),
        'total_files': len(all_chunks),
        'total_chunks': len(all_chunks),
        'total_words': sum(c.get('word_count', 0) for c in all_chunks),
        'embedding_model': 'BAAI/bge-small-zh-v1.5',
        'embedding_dim': dim,
        'bm25_documents': len(all_bm25),
        'faiss_vectors': merged_index.ntotal,
        'sources': {
            'wiki': len(existing_chunks),
            'projects': len(new_chunks) - len([c for c in new_chunks if c['category'].startswith('文献')]),
            'literature': len([c for c in new_chunks if c['category'].startswith('文献')]),
        }
    }
    
    with open(OUTPUT_DIR / 'index_summary.json', 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

def main():
    start = time.time()
    print("=" * 60)
    print("🚀 Phase 2+3: 项目文件 + PDF 文献索引")
    print("=" * 60)
    
    # Phase 2: 项目文件
    proj_chunks, proj_stats = scan_projects()
    
    # Phase 3: PDF 文献（先提取前 50 篇测试）
    pdf_files, pdf_stats = scan_pdfs()
    pdf_chunks = extract_pdfs(pdf_files, max_pdfs=50)
    
    all_new_chunks = proj_chunks + pdf_chunks
    
    if not all_new_chunks:
        print("❌ 没有找到任何内容！")
        return
    
    # 构建 BM25
    bm25, bm25_texts = build_bm25_index(all_new_chunks)
    
    # 构建 FAISS
    faiss_index, embeddings, model = build_faiss_index(all_new_chunks)
    
    # 合并
    merge_with_existing(all_new_chunks, bm25, bm25_texts, faiss_index, embeddings, model, proj_stats)
    
    elapsed = time.time() - start
    print(f"\n{'=' * 60}")
    print(f"✅ Phase 2+3 完成！耗时 {elapsed:.1f} 秒")
    print(f"   索引位置: {OUTPUT_DIR}")
    print(f"   总 chunk 数: {len(all_new_chunks)}")
    print(f"{'=' * 60}")

if __name__ == '__main__':
    main()
