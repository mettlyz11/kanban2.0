#!/usr/bin/env python3
"""
任务语义去重模块 - SDS调度系统优化
功能: 基于标题语义相似度检测重复任务
策略: 前15字精确匹配 + 语义相似度阈值0.85
"""

import os
import sys
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional, Any
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'scripts'))
from lib.db_connector import get_db_connection, execute_query, execute_update


class TaskSemanticDeduplicator:
    """任务语义去重器
    
    去重策略:
    1. 快速过滤: 前15字精确匹配 (性能优先)
    2. 语义校验: 余弦相似度 >= 0.85
    3. 时间窗口: 只检测近7天的任务
    """
    
    def __init__(self, similarity_threshold: float = 0.85, 
                 prefix_match_length: int = 15,
                 lookback_days: int = 7):
        self.similarity_threshold = similarity_threshold
        self.prefix_match_length = prefix_match_length
        self.lookback_days = lookback_days
        self._init_embeddings_table()
    
    def _init_embeddings_table(self):
        """初始化任务标题向量表"""
        sql = """
            CREATE TABLE IF NOT EXISTS task_title_embeddings (
                task_id INT PRIMARY KEY,
                title_hash VARCHAR(64) NOT NULL,
                title_prefix VARCHAR(50) NOT NULL,
                embedding TEXT,
                embedding_model VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_prefix (title_prefix),
                INDEX idx_hash (title_hash)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
        try:
            execute_update(sql, ())
        except Exception as e:
            # print(f"[WARN] 表创建可能已存在: {e}")
    
    @staticmethod
    def _get_title_prefix(title: str) -> str:
        """获取标题前缀（用于快速匹配）"""
        # 去除空格和特殊字符后取前N字
        cleaned = ''.join(title.split()).lower()
        return cleaned[:15]
    
    @staticmethod
    def _get_title_hash(title: str) -> str:
        """获取标题哈希（用于精确去重）"""
        return hashlib.sha256(title.encode('utf-8')).hexdigest()
    
    @staticmethod
    def _simple_text_similarity(text1: str, text2: str) -> float:
        """简单文本相似度计算（基于字符级ngram）
        
        不依赖外部向量模型，保证系统稳定性
        使用2-gram和3-gram的Jaccard相似度
        """
        def get_ngrams(text, n):
            cleaned = ''.join(text.lower().split())
            return set(cleaned[i:i+n] for i in range(len(cleaned) - n + 1))
        
        # 计算2-gram和3-gram相似度
        ngrams1_2 = get_ngrams(text1, 2)
        ngrams2_2 = get_ngrams(text2, 2)
        
        ngrams1_3 = get_ngrams(text1, 3)
        ngrams2_3 = get_ngrams(text2, 3)
        
        # Jaccard相似度
        def jaccard(set1, set2):
            union = len(set1 | set2)
            if union == 0:
                return 0.0
            return len(set1 & set2) / union
        
        sim_2 = jaccard(ngrams1_2, ngrams2_2)
        sim_3 = jaccard(ngrams1_3, ngrams2_3)
        
        # 加权平均: 3-gram权重更高
        return 0.4 * sim_2 + 0.6 * sim_3
    
    def _find_prefix_matches(self, title: str, exclude_task_id: int = None) -> List[Dict]:
        """查找前缀匹配的任务"""
        prefix = self._get_title_prefix(title)
        cutoff = datetime.now() - timedelta(days=self.lookback_days)
        
        sql = """
            SELECT t.id, t.title, t.created_at, t.status, t.project_id
            FROM tasks t
            LEFT JOIN task_title_embeddings e ON t.id = e.task_id
            WHERE (e.title_prefix = %s OR LEFT(REPLACE(LOWER(t.title), ' ', ''), 15) = %s)
              AND t.created_at >= %s
        """
        params = [prefix, prefix, cutoff]
        
        if exclude_task_id:
            sql += " AND t.id != %s"
            params.append(exclude_task_id)
        
        return execute_query(sql, tuple(params))
    
    def check_duplicate(self, title: str, project_id: int = None,
                        exclude_task_id: int = None) -> Dict[str, Any]:
        """检查任务是否重复
        
        Returns:
            is_duplicate: 是否重复
            duplicate_tasks: 重复任务列表
            max_similarity: 最高相似度
            matched_by: 匹配方式 ('prefix_only', 'semantic', 'exact')
        """
        # 步骤1: 精确匹配（完全相同标题）
        title_hash = self._get_title_hash(title)
        cutoff = datetime.now() - timedelta(days=self.lookback_days)
        
        exact_sql = """
            SELECT id, title, created_at, status, project_id
            FROM tasks
            WHERE title = %s AND created_at >= %s
        """
        exact_params = [title, cutoff]
        if project_id:
            exact_sql += " AND project_id = %s"
            exact_params.append(project_id)
        if exclude_task_id:
            exact_sql += " AND id != %s"
            exact_params.append(exclude_task_id)
        
        exact_matches = execute_query(exact_sql, tuple(exact_params))
        
        if exact_matches:
            return {
                'is_duplicate': True,
                'duplicate_tasks': exact_matches,
                'max_similarity': 1.0,
                'matched_by': 'exact',
                'reason': '标题完全相同'
            }
        
        # 步骤2: 前缀匹配候选
        prefix_candidates = self._find_prefix_matches(title, exclude_task_id)
        
        if project_id:
            # 优先同项目匹配
            prefix_candidates = [
                t for t in prefix_candidates 
                if t['project_id'] == project_id
            ] + [
                t for t in prefix_candidates 
                if t['project_id'] != project_id
            ]
        
        # 步骤3: 语义相似度校验
        max_sim = 0.0
        semantic_matches = []
        
        for candidate in prefix_candidates[:10]:  # 最多检查10个候选
            sim = self._simple_text_similarity(title, candidate['title'])
            max_sim = max(max_sim, sim)
            
            if sim >= self.similarity_threshold:
                candidate['similarity'] = sim
                semantic_matches.append(candidate)
        
        if semantic_matches:
            # 按相似度排序
            semantic_matches.sort(key=lambda x: x['similarity'], reverse=True)
            
            return {
                'is_duplicate': True,
                'duplicate_tasks': semantic_matches,
                'max_similarity': max_sim,
                'matched_by': 'semantic',
                'reason': f'语义相似度达到{max_sim:.3f} (阈值{self.similarity_threshold})'
            }
        
        # 无重复
        return {
            'is_duplicate': False,
            'duplicate_tasks': [],
            'max_similarity': max_sim,
            'matched_by': None,
            'reason': '未发现重复任务'
        }
    
    def register_task(self, task_id: int, title: str) -> bool:
        """注册新任务到去重系统"""
        title_prefix = self._get_title_prefix(title)
        title_hash = self._get_title_hash(title)
        
        # 先删除旧记录（如果存在）
        execute_update("DELETE FROM task_title_embeddings WHERE task_id = %s", (task_id,))
        
        sql = """
            INSERT INTO task_title_embeddings 
            (task_id, title_hash, title_prefix, embedding_model)
            VALUES (%s, %s, %s, %s)
        """
        
        try:
            execute_update(sql, (task_id, title_hash, title_prefix, 'ngram_v1'))
            return True
        except Exception as e:
            # print(f"[ERROR] 注册任务失败: {e}")
            return False
    
    def batch_register_recent_tasks(self, days: int = 30) -> int:
        """批量注册最近任务"""
        cutoff = datetime.now() - timedelta(days=days)
        sql = """
            SELECT id, title FROM tasks 
            WHERE created_at >= %s
              AND id NOT IN (SELECT task_id FROM task_title_embeddings)
        """
        tasks = execute_query(sql, (cutoff,))
        
        registered = 0
        for task in tasks:
            if self.register_task(task['id'], task['title']):
                registered += 1
        
        return registered


# 便捷函数
def safe_create_task(title: str, project_id: int, **task_kwargs) -> Dict[str, Any]:
    """安全创建任务（集成去重和频率限制）
    
    Returns:
        success: 是否成功创建
        task_id: 新任务ID
        duplicate_info: 去重检查结果
        quota_info: 频率检查结果
    """
    from task_frequency_limiter import TaskFrequencyLimiter
    
    # 步骤1: 去重检查
    dedup = TaskSemanticDeduplicator()
    dup_result = dedup.check_duplicate(title, project_id)
    
    if dup_result['is_duplicate']:
        return {
            'success': False,
            'task_id': None,
            'duplicate_info': dup_result,
            'quota_info': None,
            'reason': dup_result['reason']
        }
    
    # 步骤2: 频率限制检查
    limiter = TaskFrequencyLimiter()
    quota = limiter.get_remaining_quota(project_id)
    
    if not quota['can_generate']:
        return {
            'success': False,
            'task_id': None,
            'duplicate_info': dup_result,
            'quota_info': quota,
            'reason': f'频率超限: 本项目24小时内已生成{quota["used"]}个任务'
        }
    
    # 步骤3: 创建任务
    from lib.db_connector import execute_update
    
    sql = """
        INSERT INTO tasks (project_id, title, description, status, priority, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
    """
    
    task_id = execute_update(sql, (
        project_id,
        title,
        task_kwargs.get('description', ''),
        task_kwargs.get('status', 'pending'),
        task_kwargs.get('priority', 'medium')
    ), return_last_id=True)
    
    # 步骤4: 注册去重和频率记录
    dedup.register_task(task_id, title)
    limiter.record_task_generation(project_id, task_id, title)
    
    return {
        'success': True,
        'task_id': task_id,
        'duplicate_info': dup_result,
        'quota_info': limiter.get_remaining_quota(project_id),
        'reason': '任务创建成功'
    }


if __name__ == '__main__':
    # 简单测试
    dedup = TaskSemanticDeduplicator()
    # print("语义去重模块加载成功")
    # print(f"配置: 相似度阈值={dedup.similarity_threshold}, 前缀匹配长度={dedup.prefix_match_length}")
    
    # 测试相似度计算
    test_pairs = [
        ("完成年度体检预约", "完成年度体检预约"),
        ("完成年度体检预约", "完成年度体检"),
        ("完成年度体检预约", "预约年度体检时间"),
        ("完成年度体检预约", "购买机票"),
    ]
    
    # print("\n相似度测试:")
    for t1, t2 in test_pairs:
        sim = dedup._simple_text_similarity(t1, t2)
        status = "✓" if sim >= dedup.similarity_threshold else " "
        # print(f"  {status} [{sim:.3f}] {t1} <-> {t2}")
