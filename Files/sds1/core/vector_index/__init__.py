"""Files/ 目录向量化索引模块

提供 Files/ 目录的文档扫描、分块、向量化、检索能力
"""
from .indexer import VectorIndexer
from .search import search_documents, get_knowledge_context

__all__ = ['VectorIndexer', 'search_documents', 'get_knowledge_context']
