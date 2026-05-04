#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SDS任务语义去重器 (Task Semantic Deduplicator)
功能：基于标题语义相似度防止重复任务生成

设计依据：
- 2026年主流Agent调度系统普遍采用去重校验机制
- 双层去重：前缀快速匹配 + 语义相似度精算
- 参考OpenAI Swarm框架的任务生成最佳实践
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

import re
from typing import List, Dict, Optional, Tuple
from lib.db_connector import execute_query


class SemanticDeduplicator:
    """任务语义去重器 - 双层去重"""
    
    # 默认配置
    DEFAULT_PREFIX_LENGTH = 15
    DEFAULT_SIMILARITY_THRESHOLD = 0.85
    # 需要检查的已存在任务状态
    CHECK_STATUSES = ('pending', 'in_progress', 'completed', 'done')
    
    def __init__(self, prefix_length: int = None, similarity_threshold: float = None):
        """
        初始化去重器
        
        Args:
            prefix_length: 标题前缀匹配长度（默认15）
            similarity_threshold: 语义相似度阈值（默认0.85，0-1之间）
        """
        self.prefix_length = prefix_length if prefix_length is not None else self.DEFAULT_PREFIX_LENGTH
        self.similarity_threshold = similarity_threshold if similarity_threshold is not None else self.DEFAULT_SIMILARITY_THRESHOLD
    
    @staticmethod
    def levenshtein_distance(s1: str, s2: str) -> int:
        """
        计算两个字符串的Levenshtein编辑距离
        
        使用优化版DP，空间复杂度O(min(m,n))
        """
        if len(s1) < len(s2):
            return SemanticDeduplicator.levenshtein_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                # insert, delete, substitute
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]
    
    @classmethod
    def string_similarity(cls, s1: str, s2: str) -> float:
        """
        计算两个字符串的相似度（基于Levenshtein距离）
        
        Returns:
            相似度分数 0.0-1.0（1.0=完全相同）
        """
        if not s1 and not s2:
            return 1.0
        if not s1 or not s2:
            return 0.0
        
        max_len = max(len(s1), len(s2))
        distance = cls.levenshtein_distance(s1, s2)
        
        return 1.0 - (distance / max_len)
    
    @staticmethod
    def normalize_text(text: str) -> str:
        """
        标准化文本：去除标点、空格、大小写差异
        用于更精确的相似度比较
        """
        if not text:
            return ""
        # 转小写
        text = text.lower()
        # 去除标点符号和特殊字符（保留中英文和数字）
        text = re.sub(r'[^\w\u4e00-\u9fff]', '', text)
        # 去除多余空格
        text = text.strip()
        return text
    
    def prefix_match(self, new_title: str) -> List[Dict]:
        """
        第一层：前缀快速匹配
        查找标题前缀相同的已有任务
        
        Args:
            new_title: 新任务标题
        
        Returns:
            匹配到的已有任务列表
        """
        prefix = new_title[:self.prefix_length]
        
        # 使用 LIKE 查询前缀匹配
        sql = """
            SELECT id, title, status, project_id, created_at
            FROM tasks
            WHERE title LIKE %s
              AND status IN %s
            ORDER BY created_at DESC
        """
        like_pattern = prefix + '%'
        results = execute_query(sql, (like_pattern, self.CHECK_STATUSES))
        
        return results if results else []
    
    def semantic_check(self, new_title: str, 
                       scope_project_id: Optional[int] = None) -> List[Dict]:
        """
        第二层：语义相似度精算
        对候选任务计算语义相似度，返回超过阈值的任务
        
        Args:
            new_title: 新任务标题
            scope_project_id: 限定项目范围（None=全项目）
        
        Returns:
            相似度超过阈值的已有任务列表（含相似度分数）
        """
        candidates = []
        
        # 先做前缀匹配缩小范围
        prefix_matches = self.prefix_match(new_title)
        
        for match in prefix_matches:
            if scope_project_id and match.get('project_id') != scope_project_id:
                continue
            
            existing_title = match.get('title', '')
            
            # 标准化后计算相似度
            norm_new = self.normalize_text(new_title)
            norm_existing = self.normalize_text(existing_title)
            
            similarity = self.string_similarity(norm_new, norm_existing)
            
            # 同时也计算原始标题的相似度（避免过度标准化）
            raw_similarity = self.string_similarity(new_title, existing_title)
            
            # 取两者中较高的作为最终相似度
            final_similarity = max(similarity, raw_similarity)
            
            if final_similarity >= self.similarity_threshold:
                candidates.append({
                    'id': match['id'],
                    'title': match['title'],
                    'status': match['status'],
                    'project_id': match.get('project_id'),
                    'similarity': round(final_similarity, 4),
                    'created_at': str(match.get('created_at', '')),
                    'match_type': 'semantic'
                })
        
        # 如果前缀匹配没找到，再扫描近期同项目任务
        if not candidates and scope_project_id:
            recent = execute_query("""
                SELECT id, title, status, project_id, created_at
                FROM tasks
                WHERE project_id = %s
                  AND status IN %s
                  AND created_at >= NOW() - INTERVAL 7 DAY
                ORDER BY created_at DESC
                LIMIT 50
            """, (scope_project_id, self.CHECK_STATUSES))
            
            if recent:
                norm_new = self.normalize_text(new_title)
                for match in recent:
                    existing_title = match.get('title', '')
                    norm_existing = self.normalize_text(existing_title)
                    
                    similarity = max(
                        self.string_similarity(norm_new, norm_existing),
                        self.string_similarity(new_title, existing_title)
                    )
                    
                    if similarity >= self.similarity_threshold:
                        # 排除已在前缀匹配中找到的
                        if not any(c['id'] == match['id'] for c in candidates):
                            candidates.append({
                                'id': match['id'],
                                'title': match['title'],
                                'status': match['status'],
                                'project_id': match.get('project_id'),
                                'similarity': round(similarity, 4),
                                'created_at': str(match.get('created_at', '')),
                                'match_type': 'semantic_full_scan'
                            })
        
        # 按相似度降序
        candidates.sort(key=lambda x: x['similarity'], reverse=True)
        return candidates
    
    def is_duplicate(self, new_title: str, 
                     scope_project_id: Optional[int] = None) -> Tuple[bool, Dict]:
        """
        综合检查：是否为重复任务
        
        Args:
            new_title: 新任务标题
            scope_project_id: 限定项目范围
        
        Returns:
            (是否重复, 详细信息)
        """
        # 第一层：前缀匹配
        prefix_matches = self.prefix_match(new_title)
        
        if scope_project_id:
            prefix_matches = [
                m for m in prefix_matches 
                if m.get('project_id') == scope_project_id
            ]
        
        has_prefix_match = len(prefix_matches) > 0
        
        # 第二层：语义相似度
        semantic_matches = self.semantic_check(new_title, scope_project_id)
        
        is_dup = has_prefix_match or len(semantic_matches) > 0
        
        info = {
            'is_duplicate': is_dup,
            'new_title': new_title,
            'prefix_length': self.prefix_length,
            'similarity_threshold': self.similarity_threshold,
            'prefix_matches': len(prefix_matches),
            'semantic_matches': len(semantic_matches),
            'matched_tasks': semantic_matches if semantic_matches else [
                {
                    'id': m['id'],
                    'title': m['title'],
                    'status': m['status'],
                    'match_type': 'prefix'
                } for m in prefix_matches[:3]  # 最多返回3个
            ],
        }
        
        return is_dup, info
    
    def batch_check(self, new_titles: List[str], 
                    scope_project_id: Optional[int] = None) -> List[Dict]:
        """
        批量检查多个标题的重复性
        
        Args:
            new_titles: 新任务标题列表
            scope_project_id: 限定项目范围
        
        Returns:
            每个标题的检查结果列表
        """
        results = []
        for title in new_titles:
            is_dup, info = self.is_duplicate(title, scope_project_id)
            results.append(info)
        return results


def check_and_log(new_title: str, dedup: SemanticDeduplicator = None,
                  scope_project_id: Optional[int] = None) -> Tuple[bool, str]:
    """
    便捷函数：检查重复并返回日志消息
    """
    if dedup is None:
        dedup = SemanticDeduplicator()
    
    is_dup, info = dedup.is_duplicate(new_title, scope_project_id)
    
    if is_dup:
        match = info['matched_tasks'][0] if info['matched_tasks'] else {}
        log = (
            f"⛔ [语义去重] 发现重复任务: \"{new_title[:50]}...\"\n"
            f"   匹配: ID={match.get('id', '?')}, "
            f"相似度={match.get('similarity', 'N/A')}, "
            f"匹配类型={match.get('match_type', 'prefix')}"
        )
    else:
        log = (
            f"✅ [语义去重] \"{new_title[:50]}...\" 无重复，"
            f"前缀匹配={info['prefix_matches']}, "
            f"语义匹配={info['semantic_matches']}"
        )
    
    return not is_dup, log


if __name__ == "__main__":
    print("=" * 60)
    print("SDS任务语义去重器 - 功能测试")
    print("=" * 60)
    
    dedup = SemanticDeduplicator(prefix_length=15, similarity_threshold=0.85)
    
    # 测试内置相似度算法
    test_pairs = [
        ("Hello World", "Hello World"),
        ("Hello World", "Hello word"),
        ("和光智成商业化融资BP更新", "和光智成商业化融资计划书更新"),
        ("法务纠纷处理证据清单", "法务纠纷整理证据材料"),
        ("完全不同的标题", "完全不相关的话题"),
    ]
    
    print("\n【相似度算法测试】")
    for s1, s2 in test_pairs:
        sim = SemanticDeduplicator.string_similarity(s1, s2)
        print(f"  \"{s1}\" vs \"{s2}\"")
        print(f"  → 相似度: {sim:.4f}")
        print()
    
    # 测试数据库去重
    print("【数据库去重检查 - 示例】")
    test_titles = [
        "T1: 法务纠纷处理 - 包头九原区法院案件证据清单整理",
        "T2: 和光智成商业化 - AI材料科学2026融资BP更新",
        "全新测试任务 - 不会重复",
    ]
    
    for title in test_titles:
        is_dup, info = dedup.is_duplicate(title)
        status = "⛔ 重复" if is_dup else "✅ 无重复"
        print(f"\n  {status}: \"{title[:50]}...\"")
        if is_dup and info['matched_tasks']:
            m = info['matched_tasks'][0]
            print(f"    匹配: ID={m.get('id')}, 相似度={m.get('similarity', 'N/A')}")
