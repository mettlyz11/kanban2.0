#!/usr/bin/env python3
"""
Workspace 文件扫描器
功能：
1. 扫描 Files/ 目录下所有文档（.md, .pdf, .txt, .docx, .xlsx, .json）
2. 提取元数据（文件名、路径、修改时间、大小、项目关联）
3. 生成索引并保存到 data/workspace-index/
4. 提供检索接口供 SDS 和子代理使用

作者: SDS v4.6
创建: 2026-04-30
"""

import os
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import logging

# 日志
logger = logging.getLogger('WorkspaceScanner')

# 常量
WORKSPACE_ROOT = Path.home() / '.openclaw' / 'workspace'
FILES_DIR = WORKSPACE_ROOT / 'Files'
OUTPUT_DIR = WORKSPACE_ROOT / 'data' / 'workspace-index'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 支持的文件类型
SUPPORTED_EXTENSIONS = {
    '.md': 'markdown',
    '.txt': 'text',
    '.pdf': 'pdf',
    '.docx': 'word',
    '.xlsx': 'excel',
    '.json': 'json',
    '.py': 'python',
    '.js': 'javascript',
    '.html': 'html',
    '.csv': 'csv',
    '.yaml': 'yaml',
    '.yml': 'yaml',
    '.xml': 'xml',
}

# 忽略的模式
IGNORE_PATTERNS = [
    '.git', '__pycache__', '.pytest_cache', 'node_modules',
    '.DS_Store', '.ruff_cache', '.coverage', '.clawhub',
    'mettlyzObsidianVault.bak.',  # 备份目录
]


class FileMetadata:
    """文件元数据"""
    def __init__(self, filepath: Path):
        self.filepath = filepath
        self.relative_path = str(filepath.relative_to(WORKSPACE_ROOT))
        self.filename = filepath.name
        self.extension = filepath.suffix.lower()
        self.file_type = SUPPORTED_EXTENSIONS.get(self.extension, 'unknown')
        self.size = filepath.stat().st_size
        self.mtime = datetime.fromtimestamp(filepath.stat().st_mtime).isoformat()
        self.project_hint = self._extract_project_hint()
        self.tags = self._extract_tags()
        self.content_preview = self._get_content_preview()
        
    def _extract_project_hint(self) -> str:
        """从路径提取项目关联"""
        parts = self.relative_path.split('/')
        if len(parts) >= 2:
            # Files/Projects/xxx → Projects
            # Files/T109/xxx → T109
            return parts[1] if parts[1] != 'Files' else (parts[2] if len(parts) > 2 else '')
        return ''
    
    def _extract_tags(self) -> List[str]:
        """从文件名和路径提取标签"""
        tags = []
        text = (self.filename + ' ' + self.relative_path).lower()
        
        # 关键词标签
        keyword_tags = {
            '报告': 'report', '分析': 'analysis', '调研': 'research',
            '计划': 'plan', '方案': 'proposal', '总结': 'summary',
            '协议': 'agreement', '合同': 'contract', '法律': 'legal',
            '专利': 'patent', '论文': 'paper', '文献': 'literature',
            '财务': 'finance', '投资': 'investment', '估值': 'valuation',
            '融资': 'financing', '商业': 'business', '战略': 'strategy',
            '学术': 'academic', '教育': 'education', '家庭': 'family',
            '健康': 'health', '运动': 'exercise', '睡眠': 'sleep',
            '代码': 'code', '开发': 'development', '系统': 'system',
            'AI': 'ai', '材料': 'material', '催化': 'catalyst',
        }
        
        for cn, en in keyword_tags.items():
            if cn in text or en in text:
                tags.append(en)
        
        return list(set(tags))[:5]  # 最多5个标签
    
    def _get_content_preview(self) -> str:
        """获取内容预览（前500字）"""
        if self.file_type == 'markdown' or self.file_type == 'text':
            try:
                with open(self.filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read(2000)
                    return content[:500]
            except Exception:
                pass
        return ''
    
    def to_dict(self) -> Dict:
        return {
            'relative_path': self.relative_path,
            'filename': self.filename,
            'file_type': self.file_type,
            'size': self.size,
            'mtime': self.mtime,
            'project_hint': self.project_hint,
            'tags': self.tags,
            'content_preview': self.content_preview,
        }


class WorkspaceScanner:
    """Workspace 文件扫描器"""
    
    def __init__(self):
        self.index_data = {
            'version': '1.0',
            'last_scan': None,
            'total_files': 0,
            'by_type': {},
            'by_project': {},
            'files': [],
        }
    
    def _should_ignore(self, path: Path) -> bool:
        """检查是否应该忽略该路径"""
        path_str = str(path)
        for pattern in IGNORE_PATTERNS:
            if pattern in path_str:
                return True
        return False
    
    def scan_directory(self, directory: Path = FILES_DIR) -> List[FileMetadata]:
        """扫描目录，收集文件元数据"""
        files = []
        logger.info(f"开始扫描: {directory}")
        
        for root, dirs, filenames in os.walk(directory):
            root_path = Path(root)
            
            # 过滤忽略的目录
            dirs[:] = [d for d in dirs if not self._should_ignore(root_path / d)]
            
            for filename in filenames:
                if self._should_ignore(filename):
                    continue
                
                filepath = root_path / filename
                ext = filepath.suffix.lower()
                
                if ext in SUPPORTED_EXTENSIONS:
                    try:
                        meta = FileMetadata(filepath)
                        files.append(meta)
                    except Exception as e:
                        logger.warning(f"处理文件失败 {filepath}: {e}")
        
        logger.info(f"扫描完成: 发现 {len(files)} 个文件")
        return files
    
    def build_index(self, files: List[FileMetadata]):
        """构建索引"""
        self.index_data['last_scan'] = datetime.now().isoformat()
        self.index_data['total_files'] = len(files)
        self.index_data['files'] = [f.to_dict() for f in files]
        
        # 按类型统计
        by_type = {}
        for f in files:
            ft = f.file_type
            by_type[ft] = by_type.get(ft, 0) + 1
        self.index_data['by_type'] = by_type
        
        # 按项目统计
        by_project = {}
        for f in files:
            proj = f.project_hint or 'uncategorized'
            by_project[proj] = by_project.get(proj, 0) + 1
        self.index_data['by_project'] = by_project
    
    def save_index(self):
        """保存索引到文件"""
        index_file = OUTPUT_DIR / 'workspace_index.json'
        with open(index_file, 'w', encoding='utf-8') as f:
            json.dump(self.index_data, f, ensure_ascii=False, indent=2)
        logger.info(f"索引已保存: {index_file}")
    
    def load_index(self) -> Dict:
        """加载索引"""
        index_file = OUTPUT_DIR / 'workspace_index.json'
        if index_file.exists():
            with open(index_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return self.index_data
    
    def search(self, query: str, limit: int = 10) -> List[Dict]:
        """搜索文件（简单关键词匹配）"""
        query_lower = query.lower()
        results = []
        
        for file_info in self.index_data.get('files', []):
            score = 0
            text = (file_info['filename'] + ' ' + 
                   file_info.get('content_preview', '') + ' ' +
                   ' '.join(file_info.get('tags', []))).lower()
            
            # 标题匹配权重高
            if query_lower in file_info['filename'].lower():
                score += 10
            
            # 内容匹配
            if query_lower in text:
                score += 5
            
            # 标签匹配
            for tag in file_info.get('tags', []):
                if query_lower in tag.lower():
                    score += 3
            
            if score > 0:
                results.append({
                    **file_info,
                    'score': score
                })
        
        # 按分数排序
        results.sort(key=lambda x: x['score'], reverse=True)
        return results[:limit]
    
    def get_files_by_project(self, project_hint: str) -> List[Dict]:
        """获取指定项目的文件"""
        return [
            f for f in self.index_data.get('files', [])
            if f.get('project_hint') == project_hint
        ]
    
    def get_files_by_type(self, file_type: str) -> List[Dict]:
        """获取指定类型的文件"""
        return [
            f for f in self.index_data.get('files', [])
            if f.get('file_type') == file_type
        ]
    
    def run_full_scan(self):
        """执行完整扫描"""
        files = self.scan_directory()
        self.build_index(files)
        self.save_index()
        return {
            'total_files': len(files),
            'by_type': self.index_data['by_type'],
            'by_project': dict(sorted(self.index_data['by_project'].items(), 
                                     key=lambda x: x[1], reverse=True)[:10]),
        }


# 全局实例
_scanner_instance = None

def get_scanner() -> WorkspaceScanner:
    """获取扫描器单例"""
    global _scanner_instance
    if _scanner_instance is None:
        _scanner_instance = WorkspaceScanner()
        _scanner_instance.index_data = _scanner_instance.load_index()
    return _scanner_instance


def search_workspace_files(query: str, limit: int = 10) -> List[Dict]:
    """全局搜索接口"""
    scanner = get_scanner()
    return scanner.search(query, limit)


def refresh_workspace_index():
    """刷新索引（供SDS调用）"""
    scanner = WorkspaceScanner()
    return scanner.run_full_scan()


if __name__ == '__main__':
    # 测试运行
    logging.basicConfig(level=logging.INFO)
    scanner = WorkspaceScanner()
    result = scanner.run_full_scan()
    # print(json.dumps(result, ensure_ascii=False, indent=2))
