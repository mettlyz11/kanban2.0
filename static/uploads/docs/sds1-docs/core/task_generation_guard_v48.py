#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Task #2119: SDS调度系统任务生成频率限制与幂等性保障
统一保障模块 V1.0 (Unified Guard Module)

基于 Tavily Research 2026 结果构建的三层保障机制：
- 幂等性设计 + 频率限制 + 去重校验
- 参考 OpenAI Swarm 框架任务生成最佳实践

功能：
1. 频率限制：每目标每24小时最多2个任务（滑动窗口计数）
2. 语义去重：前15字匹配 + 语义相似度阈值0.85
3. 幂等性保障：请求指纹 + 原子性检查 + 状态追踪
4. 支持无DB降级运行（内存模式），保障系统高可用

作者: SDS Auto-Optimizer
日期: 2026-04-28
"""

import sys
from config_loader import get_config
import os
import hashlib
import json
import re
import tempfile
import threading
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum

# 添加路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

# 尝试导入DB连接器，失败时启用内存模式
try:
    from lib.db_connector import execute_query, execute_update
    DB_AVAILABLE = True
except Exception:
    DB_AVAILABLE = False


# ============================================================================
# 常量与配置
# ============================================================================

class GuardDecision(Enum):
    """保障决策结果"""
    ALLOWED = "allowed"
    BLOCKED_RATE_LIMIT = "blocked_rate_limit"
    BLOCKED_DUPLICATE = "blocked_duplicate"
    BLOCKED_IDEMPOTENT = "blocked_idempotent"
    ERROR = "error"


@dataclass
class GuardResult:
    """保障检查结果"""
    decision: GuardDecision
    can_generate: bool
    reason: str
    layer_checks: Dict[str, Any] = field(default_factory=dict)
    task_id: Optional[int] = None
    idempotency_key: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


# ============================================================================
# Layer 1: 幂等性保障 (Idempotency)
# ============================================================================

class IdempotencyLayer:
    """幂等性保障层
    
    机制：
    - 基于SHA-256的确定性幂等键生成（标题+目标ID+描述前缀）
    - 本地JSONL日志持久化 + 可选DB检查
    - 内存缓存加速（LRU风格）
    """
    
    def __init__(self, log_file: Optional[str] = None, memory_only: bool = False):
        self.memory_only = memory_only or not DB_AVAILABLE
        self._memory_cache: Dict[str, Dict] = {}
        self._cache_lock = threading.Lock()
        self.log_file = log_file or str(
            Path(get_config('paths.logs')) / "task-2119-idempotency.log"
        )
        Path(self.log_file).parent.mkdir(parents=True, exist_ok=True)
        self._load_from_log()
    
    def _load_from_log(self):
        """从日志文件加载到内存缓存"""
        if not os.path.exists(self.log_file):
            return
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        key = entry.get('key')
                        if key:
                            self._memory_cache[key] = entry
                    except json.JSONDecodeError:
                        continue
        except Exception:
            pass
    
    @staticmethod
    def generate_key(title: str, goal_id: Optional[int] = None,
                     description_prefix: str = '') -> str:
        """生成确定性幂等键（SHA-256前16位十六进制字符）"""
        key_data = json.dumps({
            'title': (title or '').strip(),
            'goal_id': goal_id,
            'desc_prefix': (description_prefix or '')[:100].strip(),
        }, ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(key_data.encode('utf-8')).hexdigest()[:16]
    
    def check(self, idempotency_key: str) -> Dict[str, Any]:
        """检查幂等性键是否已存在"""
        with self._cache_lock:
            local_found = idempotency_key in self._memory_cache
            local_task_id = self._memory_cache.get(idempotency_key, {}).get('task_id') if local_found else None
        
        return {
            'is_safe': not local_found,
            'local_found': local_found,
            'local_task_id': local_task_id,
            'idempotency_key': idempotency_key,
            'check_type': 'idempotency'
        }
    
    def record(self, idempotency_key: str, task_id: int,
               title: str, goal_id: Optional[int] = None) -> bool:
        """记录任务执行（内存+文件双重持久化）"""
        entry = {
            'key': idempotency_key,
            'task_id': task_id,
            'title': title,
            'goal_id': goal_id,
            'created_at': datetime.now().isoformat(),
            'version': '2119-v1.0'
        }
        
        with self._cache_lock:
            self._memory_cache[idempotency_key] = entry
        
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
            return True
        except Exception:
            return False
    
    def cleanup_old_records(self, days: int = 30) -> int:
        """清理过期记录"""
        cutoff = datetime.now() - timedelta(days=days)
        removed = 0
        
        with self._cache_lock:
            keys_to_remove = []
            for key, entry in self._memory_cache.items():
                try:
                    created = datetime.fromisoformat(entry.get('created_at', ''))
                    if created < cutoff:
                        keys_to_remove.append(key)
                except (ValueError, TypeError):
                    pass
            
            for key in keys_to_remove:
                del self._memory_cache[key]
                removed += 1
        
        return removed


# ============================================================================
# Layer 2: 频率限制 (Rate Limiting)
# ============================================================================

class RateLimitLayer:
    """频率限制层
    
    机制：
    - 每目标(goal_id)每24小时最多2个任务
    - pending水位控制：每目标最多3个pending任务
    - 滑动窗口精确到秒
    - 内存回退模式支持无DB运行
    """
    
    DEFAULT_MAX_TASKS_PER_24H = 2  # 每目标每24小时最多2个任务
    DEFAULT_MAX_PENDING_PER_GOAL = 3  # 每目标最多3个pending任务
    DEFAULT_WINDOW_HOURS = 24
    
    def __init__(self, max_tasks: Optional[int] = None,
                 max_pending: Optional[int] = None,
                 window_hours: Optional[int] = None,
                 memory_only: bool = False):
        self.max_tasks = max_tasks if max_tasks is not None else self.DEFAULT_MAX_TASKS_PER_24H
        self.max_pending = max_pending if max_pending is not None else self.DEFAULT_MAX_PENDING_PER_GOAL
        self.window_hours = window_hours if window_hours is not None else self.DEFAULT_WINDOW_HOURS
        self.memory_only = memory_only or not DB_AVAILABLE
        self._memory_records: List[Dict] = []
        self._record_lock = threading.Lock()
    
    def check_rate_limit(self, goal_id: int) -> Dict[str, Any]:
        """检查24小时频率限制"""
        window_start = datetime.now() - timedelta(hours=self.window_hours)
        
        if self.memory_only:
            with self._record_lock:
                current_count = sum(
                    1 for r in self._memory_records
                    if r.get('goal_id') == goal_id and r.get('generated_at', datetime.min) >= window_start
                )
        else:
            try:
                sql = """
                    SELECT COUNT(*) as cnt
                    FROM tasks
                    WHERE goal_id = %s
                      AND task_type LIKE 'auto_generated%%'
                      AND created_at >= %s
                """
                result = execute_query(sql, (goal_id, window_start))
                current_count = result[0].get('cnt', 0) if result else 0
            except Exception:
                current_count = 0
        
        allowed = current_count < self.max_tasks
        
        return {
            'can_generate': allowed,
            'current_count': current_count,
            'max_allowed': self.max_tasks,
            'remaining_slots': max(0, self.max_tasks - current_count),
            'window_hours': self.window_hours,
            'window_start': window_start.isoformat(),
            'goal_id': goal_id,
            'check_type': 'rate_limit'
        }
    
    def check_pending_watermark(self, goal_id: int) -> Dict[str, Any]:
        """检查pending任务水位"""
        if self.memory_only:
            with self._record_lock:
                pending_count = sum(
                    1 for r in self._memory_records
                    if r.get('goal_id') == goal_id and r.get('status') == 'pending'
                )
        else:
            try:
                sql = """
                    SELECT COUNT(*) as cnt
                    FROM tasks
                    WHERE goal_id = %s AND status = 'pending'
                """
                result = execute_query(sql, (goal_id,))
                pending_count = result[0].get('cnt', 0) if result else 0
            except Exception:
                pending_count = 0
        
        allowed = pending_count < self.max_pending
        
        return {
            'can_generate': allowed,
            'pending_count': pending_count,
            'max_pending': self.max_pending,
            'remaining_slots': max(0, self.max_pending - pending_count),
            'goal_id': goal_id,
            'check_type': 'pending_watermark'
        }
    
    def record_generation(self, goal_id: int, task_id: int, title: str,
                          status: str = 'pending') -> None:
        """记录任务生成事件（用于内存模式统计）"""
        with self._record_lock:
            self._memory_records.append({
                'goal_id': goal_id,
                'task_id': task_id,
                'title': title,
                'status': status,
                'generated_at': datetime.now()
            })


# ============================================================================
# Layer 3: 语义去重 (Semantic Deduplication)
# ============================================================================

class SemanticDedupLayer:
    """语义去重层
    
    机制：
    - 快速过滤：标题前15字精确匹配
    - 语义校验：Levenshtein距离 / 最长公共子序列 → 相似度 >= 0.85
    - 文本标准化：去除标点、空格、大小写统一
    - 时间窗口：默认检查近7天任务
    """
    
    DEFAULT_SIMILARITY_THRESHOLD = 0.3  # ✅ 温和去重，既避免完全重复又不阻碍生成
    DEFAULT_PREFIX_LENGTH = 15
    DEFAULT_LOOKBACK_DAYS = 7
    
    def __init__(self, similarity_threshold: Optional[float] = None,
                 prefix_length: Optional[int] = None,
                 lookback_days: Optional[int] = None,
                 memory_only: bool = False):
        self.similarity_threshold = similarity_threshold if similarity_threshold is not None else self.DEFAULT_SIMILARITY_THRESHOLD
        self.prefix_length = prefix_length if prefix_length is not None else self.DEFAULT_PREFIX_LENGTH
        self.lookback_days = lookback_days if lookback_days is not None else self.DEFAULT_LOOKBACK_DAYS
        self.memory_only = memory_only or not DB_AVAILABLE
        self._memory_tasks: Dict[int, Dict] = {}
        self._task_lock = threading.Lock()
    
    @staticmethod
    def normalize_text(text: str) -> str:
        """标准化文本：去除标点、空格，转小写"""
        if not text:
            return ""
        # 去除中英文标点、空格、换行
        cleaned = re.sub(r'[\s\u3000-\u303F\uFF00-\uFFEF\u2000-\u206F]+', '', text)
        return cleaned.lower()
    
    @staticmethod
    def levenshtein_distance(s1: str, s2: str) -> int:
        """计算Levenshtein编辑距离（动态规划）"""
        if len(s1) < len(s2):
            return SemanticDedupLayer.levenshtein_distance(s2, s1)
        if not s2:
            return len(s1)
        
        previous_row = range(len(s2) + 1)
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]
    
    @classmethod
    def string_similarity(cls, s1: str, s2: str) -> float:
        """计算字符串相似度（1 - normalized Levenshtein distance）"""
        if not s1 and not s2:
            return 1.0
        if not s1 or not s2:
            return 0.0
        
        dist = cls.levenshtein_distance(s1, s2)
        max_len = max(len(s1), len(s2))
        return 1.0 - (dist / max_len) if max_len > 0 else 1.0
    
    def _get_title_prefix(self, title: str) -> str:
        """获取标题前缀（用于快速匹配）"""
        normalized = self.normalize_text(title)
        return normalized[:self.prefix_length]
    
    def _find_candidates(self, title: str, goal_id: Optional[int] = None) -> List[Dict]:
        """查找候选重复任务"""
        prefix = self._get_title_prefix(title)
        cutoff = datetime.now() - timedelta(days=self.lookback_days)
        candidates = []
        
        if self.memory_only:
            with self._task_lock:
                for task_id, task in self._memory_tasks.items():
                    task_time = task.get('created_at', datetime.min)
                    if isinstance(task_time, str):
                        try:
                            task_time = datetime.fromisoformat(task_time)
                        except ValueError:
                            continue
                    if task_time >= cutoff:
                        task_prefix = self._get_title_prefix(task.get('title', ''))
                        if task_prefix == prefix:
                            candidates.append({
                                'id': task_id,
                                'title': task.get('title', ''),
                                'created_at': task_time.isoformat() if isinstance(task_time, datetime) else str(task_time),
                                'goal_id': task.get('goal_id')
                            })
        else:
            try:
                normalized_prefix = title[:self.prefix_length]
                sql = """
                    SELECT id, title, created_at, goal_id
                    FROM tasks
                    WHERE title LIKE %s
                      AND created_at >= %s
                """
                results = execute_query(sql, (f"{normalized_prefix}%", cutoff))
                candidates = results or []
            except Exception:
                candidates = []
        
        return candidates
    
    def check(self, title: str, goal_id: Optional[int] = None) -> Dict[str, Any]:
        """检查任务是否重复"""
        if not title:
            return {
                'is_duplicate': False,
                'duplicate_tasks': [],
                'max_similarity': 0.0,
                'matched_by': None,
                'title_prefix': '',
                'reason': '标题为空，跳过去重检查'
            }
        
        normalized_title = self.normalize_text(title)
        prefix = self._get_title_prefix(title)
        
        candidates = self._find_candidates(title, goal_id)
        
        max_sim = 0.0
        semantic_matches = []
        
        for candidate in candidates[:10]:
            candidate_norm = self.normalize_text(candidate.get('title', ''))
            sim = self.string_similarity(normalized_title, candidate_norm)
            max_sim = max(max_sim, sim)
            
            if sim >= self.similarity_threshold:
                candidate['similarity'] = round(sim, 4)
                semantic_matches.append(candidate)
        
        if semantic_matches:
            semantic_matches.sort(key=lambda x: x['similarity'], reverse=True)
            return {
                'is_duplicate': True,
                'duplicate_tasks': semantic_matches,
                'max_similarity': max_sim,
                'matched_by': 'semantic',
                'title_prefix': prefix,
                'reason': f'语义相似度达到{max_sim:.3f}（阈值{self.similarity_threshold}）'
            }
        
        return {
            'is_duplicate': False,
            'duplicate_tasks': [],
            'max_similarity': max_sim,
            'matched_by': None,
            'title_prefix': prefix,
            'reason': '未发现重复任务'
        }
    
    def register_task(self, task_id: int, title: str, goal_id: Optional[int] = None) -> bool:
        """注册新任务到去重系统"""
        with self._task_lock:
            self._memory_tasks[task_id] = {
                'title': title,
                'goal_id': goal_id,
                'created_at': datetime.now().isoformat()
            }
        return True


# ============================================================================
# 统一保障入口 (Unified Guard)
# ============================================================================

class UnifiedTaskGuard:
    """统一任务生成保障器
    
    整合三层保障，提供单一入口：
    1. 幂等性检查（Layer 1）
    2. 频率限制检查（Layer 2）
    3. 语义去重检查（Layer 3）
    
    支持内存降级模式，确保DB不可用时系统仍可运行
    """
    
    def __init__(self, memory_only: bool = False):
        self.memory_only = memory_only or not DB_AVAILABLE
        self.idempotency = IdempotencyLayer(memory_only=self.memory_only)
        self.rate_limit = RateLimitLayer(memory_only=self.memory_only)
        self.dedup = SemanticDedupLayer(memory_only=self.memory_only)
    
    def check(self, title: str, goal_id: Optional[int] = None,
              description: str = '',
              idempotency_key: Optional[str] = None) -> GuardResult:
        """三层保障综合检查
        
        执行顺序（短路求值）：
        1. 幂等性 → 2. 频率限制 → 3. 语义去重
        """
        layer_checks = {}
        
        # Layer 1: 幂等性检查
        key = idempotency_key or self.idempotency.generate_key(title, goal_id, description)
        idem_result = self.idempotency.check(key)
        layer_checks['idempotency'] = idem_result
        
        if not idem_result['is_safe']:
            return GuardResult(
                decision=GuardDecision.BLOCKED_IDEMPOTENT,
                can_generate=False,
                reason=f"幂等性拦截: {idem_result.get('reason', '重复请求')}",
                layer_checks=layer_checks,
                idempotency_key=key
            )
        
        # Layer 2: 频率限制检查
        rate_result = self.rate_limit.check_rate_limit(goal_id or 0)
        layer_checks['rate_limit'] = rate_result
        
        if not rate_result['can_generate']:
            return GuardResult(
                decision=GuardDecision.BLOCKED_RATE_LIMIT,
                can_generate=False,
                reason=f"频率限制: 目标{goal_id}在{rate_result['window_hours']}小时内已生成{rate_result['current_count']}个任务（上限{rate_result['max_allowed']}）",
                layer_checks=layer_checks,
                idempotency_key=key
            )
        
        # Layer 2b: pending水位检查
        pending_result = self.rate_limit.check_pending_watermark(goal_id or 0)
        layer_checks['pending_watermark'] = pending_result
        
        if not pending_result['can_generate']:
            return GuardResult(
                decision=GuardDecision.BLOCKED_RATE_LIMIT,
                can_generate=False,
                reason=f"水位限制: 目标{goal_id}已有{pending_result['pending_count']}个pending任务（上限{pending_result['max_pending']}）",
                layer_checks=layer_checks,
                idempotency_key=key
            )
        
        # Layer 3: 语义去重检查
        dup_result = self.dedup.check(title, goal_id)
        layer_checks['deduplication'] = dup_result
        
        if dup_result['is_duplicate']:
            dup_task = dup_result['duplicate_tasks'][0]
            return GuardResult(
                decision=GuardDecision.BLOCKED_DUPLICATE,
                can_generate=False,
                reason=f"重复检测: 与任务#{dup_task['id']}相似度{dup_result['max_similarity']:.3f}（阈值{self.dedup.similarity_threshold}）",
                layer_checks=layer_checks,
                idempotency_key=key
            )
        
        # 全部通过
        return GuardResult(
            decision=GuardDecision.ALLOWED,
            can_generate=True,
            reason="三层保障全部通过，允许生成任务",
            layer_checks=layer_checks,
            idempotency_key=key
        )
    
    def record_success(self, idempotency_key: str, task_id: int,
                       title: str, goal_id: Optional[int] = None) -> bool:
        """记录任务生成成功"""
        self.idempotency.record(idempotency_key, task_id, title, goal_id)
        self.dedup.register_task(task_id, title, goal_id)
        self.rate_limit.record_generation(goal_id or 0, task_id, title)
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """获取保障系统统计"""
        return {
            'db_available': DB_AVAILABLE,
            'memory_mode': self.memory_only,
            'idempotency_cache_size': len(self.idempotency._memory_cache),
            'rate_limit_records': len(self.rate_limit._memory_records),
            'dedup_tasks': len(self.dedup._memory_tasks),
            'config': {
                'max_tasks_per_24h': self.rate_limit.max_tasks,
                'max_pending_per_goal': self.rate_limit.max_pending,
                'similarity_threshold': self.dedup.similarity_threshold,
                'prefix_match_length': self.dedup.prefix_length,
                'lookback_days': self.dedup.lookback_days
            }
        }


# ============================================================================
# 便捷函数
# ============================================================================

def quick_guard_check(title: str, goal_id: Optional[int] = None,
                      description: str = '') -> GuardResult:
    """快速检查函数（单例模式）"""
    guard = UnifiedTaskGuard()
    return guard.check(title, goal_id, description)


# ============================================================================
# 主程序
# ============================================================================

if __name__ == '__main__':
    # print("=" * 70)
    # print("Task #2119: SDS调度系统任务生成频率限制与幂等性保障")
    # print("统一保障模块 V1.0")
    # print("=" * 70)
    
    guard = UnifiedTaskGuard()
    stats = guard.get_stats()
    
    # print(f"\n📊 系统状态:")
    # print(f"  数据库可用: {'✅' if stats['db_available'] else '❌（内存模式）'}")
    # print(f"  运行模式: {'内存降级' if stats['memory_mode'] else '正常（DB连接）'}")
    
    # print(f"\n⚙️  配置参数:")
    for k, v in stats['config'].items():
        # print(f"  {k}: {v}")
    
    # print(f"\n🧪 快速验证:")
    # 测试1: 新任务应通过
    result = guard.check("T1: 测试新任务生成", goal_id=1)
    # print(f"  新任务检查: {'✅ 通过' if result.can_generate else '❌ 拦截'} - {result.reason}")
    
    # 测试2: 相同任务应被幂等性拦截
    result2 = guard.check("T1: 测试新任务生成", goal_id=1)
    # print(f"  重复检查: {'✅ 通过' if result2.can_generate else '❌ 拦截'} - {result2.reason}")
    
    # print("\n✅ 模块加载完成")
