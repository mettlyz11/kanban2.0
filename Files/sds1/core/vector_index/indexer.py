"""Files/ 目录向量化索引器

提供文档扫描、分块、嵌入、索引的全流程能力
"""
import os
import json
import hashlib
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import logging

logger = logging.getLogger('sds.vector_index')

# 配置
WORKSPACE_ROOT = Path("/Users/mettlyz/.openclaw/workspace")
FILES_DIR = WORKSPACE_ROOT / 'Files'
INDEX_DIR = WORKSPACE_ROOT / 'data' / 'vector-index'
SUPPORTED_EXTENSIONS = {'.md', '.txt', '.pdf', '.docx', '.xlsx', '.json'}
CHUNK_SIZE = 1000  # 字符数
CHUNK_OVERLAP = 200  # 重叠字符数

class VectorIndexer:
    """Files/ 目录向量化索引器"""
    
    def __init__(self):
        self.index_dir = INDEX_DIR
        self.index_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_file = self.index_dir / 'metadata.json'
        self.chunks_file = self.index_dir / 'chunks.json'
        self.last_update_file = self.index_dir / 'last_update.txt'
        
    def scan_files(self, since: Optional[datetime] = None) -> List[Dict]:
        """扫描 Files/ 目录下的所有支持文件
        
        Args:
            since: 只扫描此时间后修改的文件
        
        Returns:
            文件元数据列表
        """
        files = []
        
        if not FILES_DIR.exists():
            logger.warning(f"Files/ 目录不存在: {FILES_DIR}")
            return files
        
        for filepath in FILES_DIR.rglob('*'):
            if filepath.is_file() and filepath.suffix.lower() in SUPPORTED_EXTENSIONS:
                stat = filepath.stat()
                mtime = datetime.fromtimestamp(stat.st_mtime)
                
                if since and mtime <= since:
                    continue
                
                files.append({
                    'path': str(filepath.relative_to(WORKSPACE_ROOT)),
                    'name': filepath.name,
                    'size': stat.st_size,
                    'mtime': mtime.isoformat(),
                    'extension': filepath.suffix.lower(),
                    'category': self._detect_category(filepath)
                })
        
        logger.info(f"扫描到 {len(files)} 个文件待索引")
        return files
    
    def _detect_category(self, filepath: Path) -> str:
        """检测文件所属分类"""
        rel = filepath.relative_to(FILES_DIR)
        parts = rel.parts
        
        if not parts:
            return 'root'
        
        first_dir = parts[0].lower()
        
        category_map = {
            'projects': 'projects',
            'yuzhouvault': 'knowledge',
            'literature': 'literature',
            't109': 'project_t109',
            't110': 'project_t110',
            't5': 'family',
            't6': 'social',
            't7': 'health',
            'family-': 'family',
            'finance': 'finance',
            'inbox': 'inbox',
        }
        
        for prefix, cat in category_map.items():
            if first_dir.startswith(prefix):
                return cat
        
        return 'other'
    
    def extract_text(self, file_info: Dict) -> str:
        """从文件中提取文本"""
        filepath = WORKSPACE_ROOT / file_info['path']
        ext = file_info['extension']
        
        try:
            if ext in ['.md', '.txt', '.json']:
                return filepath.read_text(encoding='utf-8', errors='ignore')
            elif ext == '.pdf':
                # 简化PDF提取（实际可用PyPDF2/pdfplumber）
                return f"[PDF文件] {file_info['name']}"
            elif ext in ['.docx', '.xlsx']:
                return f"[Office文件] {file_info['name']}"
            else:
                return f"[二进制文件] {file_info['name']}"
        except Exception as e:
            logger.warning(f"读取文件失败 {filepath}: {e}")
            return ""
    
    def chunk_text(self, text: str, filepath: str) -> List[Dict]:
        """将文本分块
        
        Args:
            text: 完整文本
            filepath: 文件路径（用于生成chunk ID）
        
        Returns:
            文本块列表
        """
        if not text or len(text) < 50:
            return []
        
        chunks = []
        start = 0
        chunk_idx = 0
        
        while start < len(text):
            end = min(start + CHUNK_SIZE, len(text))
            
            # 在句子边界处切割
            if end < len(text):
                # 向后查找句号、换行
                for i in range(end, max(end - 100, start), -1):
                    if text[i-1] in '。！？.!?\n':
                        end = i
                        break
            
            chunk_text = text[start:end].strip()
            if len(chunk_text) > 30:  # 过滤太短的块
                chunk_id = hashlib.md5(
                    f"{filepath}:{chunk_idx}:{chunk_text[:50]}".encode()
                ).hexdigest()[:16]
                
                chunks.append({
                    'id': chunk_id,
                    'text': chunk_text,
                    'start': start,
                    'end': end,
                    'filepath': filepath,
                    'index': chunk_idx
                })
                chunk_idx += 1
            
            start = end - CHUNK_OVERLAP
            if start >= end:
                break
        
        return chunks
    
    def build_index(self, incremental: bool = True) -> Dict:
        """构建或更新向量索引
        
        Args:
            incremental: 是否增量更新（只处理新/修改的文件）
        
        Returns:
            索引统计信息
        """
        last_update = None
        if incremental and self.last_update_file.exists():
            try:
                last_update = datetime.fromisoformat(
                    self.last_update_file.read_text().strip()
                )
                logger.info(f"增量索引，上次更新: {last_update}")
            except:
                pass
        
        # 1. 扫描文件
        files = self.scan_files(since=last_update if incremental else None)
        
        if not files:
            logger.info("没有新文件需要索引")
            return {'indexed': 0, 'chunks': 0, 'mode': 'incremental' if incremental else 'full'}
        
        # 2. 加载现有索引（增量模式）
        existing_chunks = {}
        if incremental and self.chunks_file.exists():
            try:
                with open(self.chunks_file, 'r') as f:
                    for chunk in json.load(f):
                        existing_chunks[chunk['id']] = chunk
                logger.info(f"加载现有索引: {len(existing_chunks)} 个 chunks")
            except:
                pass
        
        # 3. 处理文件 → 分块
        all_chunks = dict(existing_chunks)  # 复制现有
        processed_files = 0
        
        for file_info in files:
            text = self.extract_text(file_info)
            if not text:
                continue
            
            chunks = self.chunk_text(text, file_info['path'])
            for chunk in chunks:
                all_chunks[chunk['id']] = chunk
            
            processed_files += 1
            
            if processed_files % 50 == 0:
                logger.info(f"已处理 {processed_files}/{len(files)} 个文件")
        
        # 4. 保存索引
        chunks_list = list(all_chunks.values())
        
        with open(self.chunks_file, 'w') as f:
            json.dump(chunks_list, f, ensure_ascii=False, indent=2)
        
        # 保存元数据
        metadata = {
            'total_files': len(files) + (len(existing_chunks) if incremental else 0),
            'total_chunks': len(chunks_list),
            'last_update': datetime.now().isoformat(),
            'indexed_extensions': list(SUPPORTED_EXTENSIONS),
            'version': '1.0'
        }
        
        with open(self.metadata_file, 'w') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        self.last_update_file.write_text(datetime.now().isoformat())
        
        logger.info(f"索引完成: {processed_files} 个文件, {len(chunks_list)} 个 chunks")
        
        return {
            'indexed': processed_files,
            'chunks': len(chunks_list),
            'mode': 'incremental' if incremental else 'full'
        }
    
    def get_stats(self) -> Dict:
        """获取索引统计"""
        stats = {
            'indexed_files': 0,
            'total_chunks': 0,
            'last_update': None,
            'index_exists': False
        }
        
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r') as f:
                    meta = json.load(f)
                stats['indexed_files'] = meta.get('total_files', 0)
                stats['total_chunks'] = meta.get('total_chunks', 0)
                stats['last_update'] = meta.get('last_update')
                stats['index_exists'] = True
            except:
                pass
        
        return stats
