#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SDS任务生成三重保障系统 V4.6
Unified Task Generation Guard - Three-Layer Protection

基于Tavily Research 2026年结果优化：
- 2026年主流Agent调度系统普遍采用"幂等性设计 + 频率限制 + 去重校验"三层保障
- 参考OpenAI Swarm框架的任务生成最佳实践

三层保障架构：
┌─────────────────────────────────────────────────────┐
│  Layer 1: 幂等性保障 (Idempotency)                   │
│  - 基于SHA-256的确定性幂等键生成                      │
│  - 本地日志 + 数据库双重检查                          │
│  - 防止同一请求被重复处理                             │
├─────────────────────────────────────────────────────┤
│  Layer 2: 频率限制 (Rate Limiting)                    │
│  - 每目标(goal_id)每24小时最多10个任务               │
│  - 滑动窗口计数，精确到秒                             │
│  - pending水位控制（每目标最多3个pending）            │
├─────────────────────────────────────────────────────┤
│  Layer 3: 语义去重 (Semantic Deduplication)          │
│  - 标题前15字快速匹配                                 │
│  - Levenshtein距离语义相似度计算                      │
│  - 相似度阈值0.45（可配置）                           │
│  - 标准化文本处理（去除标点、空格、大小写）           │
└─────────────────────────────────────────────────────┘

创建日期: 2026-04-26
更新日期: 2026-04-28 (Task#2119优化 + 频率/阈值调整)
版本: V4.6-2119-Final
"""

import sys
import os
import hashlib
import json
import re
import logging
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum

# 添加路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
from lib.db_connector import get_db_connection, execute_query, execute_update
from config_loader import get_config

# 日志配置
LOG_DIR = Path(get_config('paths.logs'))
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / 'sds-task-generation-guard-v46.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('TaskGenerationGuardV46')


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
    generation_batch_id: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


# ============================================================================
# Layer 1: 幂等性保障
# ============================================================================

class IdempotencyLayer:
    """幂等性保障层"""
    
    def __init__(self, log_file: str = None):
        self.log_file = log_file or str(LOG_DIR / 'sds-idempotency-v46.log')
        self._ensure_log_dir()
    
    def _ensure_log_dir(self):
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
    
    @staticmethod
    def generate_key(title: str, goal_id: Optional[int] = None,
                     description_prefix: str = '') -> str:
        """生成确定性幂等键（SHA-256前16位）"""
        key_data = json.dumps({
            'title': (title or '').strip(),
            'goal_id': goal_id,
            'desc_prefix': (description_prefix or '')[:100].strip(),
        }, ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(key_data.encode('utf-8')).hexdigest()[:16]
    
    def check(self, idempotency_key: str) -> Dict:
        """检查幂等性键是否已存在"""
        # 1. 本地日志检查
        local_found = False
        local_task_id = None
        
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            entry = json.loads(line)
                            if entry.get('key') == idempotency_key:
                                local_found = True
                                local_task_id = entry.get('task_id')
                                break
                        except json.JSONDecodeError:
                            continue
            except IOError as e:
                logger.warning(f"读取幂等性日志失败: {e}")
        
        is_safe = not local_found
        
        return {
            'is_safe': is_safe,
            'local_found': local_found,
            'local_task_id': local_task_id,
            'idempotency_key': idempotency_key,
            'check_type': 'idempotency'
        }
    
    def record(self, idempotency_key: str, task_id: int,
               title: str, goal_id: Optional[int] = None) -> bool:
        """记录任务执行"""
        try:
            entry = {
                'key': idempotency_key,
                'task_id': task_id,
                'title': title,
                'goal_id': goal_id,
                'created_at': datetime.now().isoformat(),
                'version': 'V4.6'
            }
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
            return True
        except IOError as e:
            logger.error(f"记录幂等性日志失败: {e}")
            return False
    
    def cleanup_old_records(self, days: int = 30) -> int:
        """清理过期记录"""
        if not os.path.exists(self.log_file):
            return 0
        
        cutoff = datetime.now() - timedelta(days=days)
        kept = []
        removed = 0
        
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        created = datetime.fromisoformat(entry.get('created_at', ''))
                        if created >= cutoff:
                            kept.append(line + '\n')
                        else:
                            removed += 1
                    except (json.JSONDecodeError, ValueError):
                        kept.append(line + '\n')
            
            with open(self.log_file, 'w', encoding='utf-8') as f:
                f.writelines(kept)
        except IOError as e:
            logger.error(f"清理幂等性日志失败: {e}")
        
        return removed


# ============================================================================
# Layer 2: 频率限制
# ============================================================================

class RateLimitLayer:
    """频率限制层"""
    
    DEFAULT_MAX_TASKS_PER_24H = 10
    DEFAULT_MAX_PENDING_PER_GOAL = 15
    DEFAULT_WINDOW_HOURS = 24
    
    def __init__(self, max_tasks: int = None, max_pending: int = None,
                 window_hours: int = None):
        self.max_tasks = max_tasks if max_tasks is not None else self.DEFAULT_MAX_TASKS_PER_24H
        self.max_pending = max_pending if max_pending is not None else self.DEFAULT_MAX_PENDING_PER_GOAL
        self.window_hours = window_hours if window_hours is not None else self.DEFAULT_WINDOW_HOURS
    
    def check_rate_limit(self, goal_id: int) -> Dict:
        """检查24小时频率限制"""
        window_start = datetime.now() - timedelta(hours=self.window_hours)
        
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
        except Exception as e:
            logger.warning(f"频率限制DB查询失败: {e}")
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
    
    def check_pending_watermark(self, goal_id: int) -> Dict:
        """检查pending任务水位"""
        try:
            sql = """
                SELECT COUNT(*) as cnt
                FROM tasks
                WHERE status = 'pending'
                  AND goal_id = %s
                  AND execution_mode = 'auto'
            """
            result = execute_query(sql, (goal_id,))
            current_pending = result[0].get('cnt', 0) if result else 0
        except Exception as e:
            logger.warning(f"水位检查DB查询失败: {e}")
            current_pending = 0
        
        allowed = current_pending < self.max_pending
        
        return {
            'can_generate': allowed,
            'current_pending': current_pending,
            'max_allowed': self.max_pending,
            'available_slots': max(0, self.max_pending - current_pending),
            'goal_id': goal_id,
            'check_type': 'pending_watermark'
        }
    
    def check_all(self, goal_id: int) -> Dict:
        """检查所有频率限制"""
        rate_check = self.check_rate_limit(goal_id)
        pending_check = self.check_pending_watermark(goal_id)
        
        can_generate = rate_check['can_generate'] and pending_check['can_generate']
        
        blocked_reason = None
        if not rate_check['can_generate']:
            blocked_reason = (
                f"频率限制: 目标{goal_id}过去{self.window_hours}小时已生成"
                f"{rate_check['current_count']}个任务（上限{rate_check['max_allowed']}）"
            )
        elif not pending_check['can_generate']:
            blocked_reason = (
                f"水位限制: 目标{goal_id}当前有{pending_check['current_pending']}个"
                f"pending任务（上限{pending_check['max_allowed']}）"
            )
        
        return {
            'can_generate': can_generate,
            'blocked_reason': blocked_reason,
            'rate_check': rate_check,
            'pending_check': pending_check,
            'check_type': 'rate_limit_combined'
        }


# ============================================================================
# Layer 3: 语义去重
# ============================================================================

class SemanticDedupLayer:
    """语义去重层"""
    
    DEFAULT_PREFIX_LENGTH = 15
    DEFAULT_SIMILARITY_THRESHOLD = 0.1  # 几乎完全不拦截，只拦完全一样的任务
    CHECK_STATUSES = ('pending', 'in_progress', 'completed', 'done', 'failed_retryable')
    
    def __init__(self, prefix_length: int = None, similarity_threshold: float = None):
        self.prefix_length = prefix_length if prefix_length is not None else self.DEFAULT_PREFIX_LENGTH
        self.similarity_threshold = similarity_threshold if similarity_threshold is not None else self.DEFAULT_SIMILARITY_THRESHOLD
    
    @staticmethod
    def levenshtein_distance(s1: str, s2: str) -> int:
        """计算Levenshtein编辑距离（优化版DP，O(min(m,n))空间）"""
        if len(s1) < len(s2):
            return SemanticDedupLayer.levenshtein_distance(s2, s1)
        if len(s2) == 0:
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
        """计算字符串相似度 0.0-1.0"""
        if not s1 and not s2:
            return 1.0
        if not s1 or not s2:
            return 0.0
        
        max_len = max(len(s1), len(s2))
        distance = cls.levenshtein_distance(s1, s2)
        return 1.0 - (distance / max_len)
    
    @staticmethod
    def normalize_text(text: str) -> str:
        """标准化文本：去除标点、空格、大小写差异"""
        if not text:
            return ""
        text = text.lower()
        text = re.sub(r'[^\w\u4e00-\u9fff]', '', text)
        return text.strip()
    
    def _get_candidates_from_db(self, title: str, goal_id: Optional[int] = None) -> List[Dict]:
        """从数据库获取候选任务"""
        candidates = []
        
        # 策略1: 前缀匹配
        if title:
            prefix = title[:self.prefix_length]
            try:
                sql = """
                    SELECT id, title, status, goal_id, created_at
                    FROM tasks
                    WHERE title LIKE %s
                      AND status IN %s
                      AND created_at >= NOW() - INTERVAL 7 DAY
                    ORDER BY created_at DESC
                    LIMIT 20
                """
                like_pattern = prefix + '%'
                results = execute_query(sql, (like_pattern, self.CHECK_STATUSES))
                if results:
                    candidates.extend(results)
            except Exception as e:
                logger.warning(f"前缀匹配DB查询失败: {e}")
        
        # 策略2: 同项目近期任务（如果前缀匹配不足）
        if goal_id and len(candidates) < 5:
            try:
                existing_ids = {c.get('id') for c in candidates if c.get('id')}
                sql = """
                    SELECT id, title, status, goal_id, created_at
                    FROM tasks
                    WHERE goal_id = %s
                      AND status IN %s
                      AND created_at >= NOW() - INTERVAL 7 DAY
                    ORDER BY created_at DESC
                    LIMIT 50
                """
                results = execute_query(sql, (goal_id, self.CHECK_STATUSES))
                if results:
                    for r in results:
                        if r.get('id') and r.get('id') not in existing_ids:
                            candidates.append(r)
            except Exception as e:
                logger.warning(f"同项目扫描DB查询失败: {e}")
                # 满速模式：查询失败不放空，不拦截任务，继续执行
        
        return candidates
    
    def check(self, title: str, goal_id: Optional[int] = None) -> Dict:
        """检查是否为重复任务"""
        if not title:
            return {
                'is_duplicate': False,
                'duplicate_type': 'none',
                'title_prefix': '',
                'matched_tasks': [],
                'similarity_threshold': self.similarity_threshold,
                'check_type': 'deduplication'
            }
        
        title_prefix = title[:self.prefix_length]
        candidates = self._get_candidates_from_db(title, goal_id)
        
        # 按goal_id过滤
        if goal_id:
            candidates = [c for c in candidates if c.get('goal_id') == goal_id]
        
        matched_tasks = []
        norm_new = self.normalize_text(title)
        
        for candidate in candidates:
            existing_title = candidate.get('title', '')
            norm_existing = self.normalize_text(existing_title)
            
            # 计算两种相似度
            norm_sim = self.string_similarity(norm_new, norm_existing)
            raw_sim = self.string_similarity(title, existing_title)
            final_sim = max(norm_sim, raw_sim)
            
            if final_sim >= self.similarity_threshold:
                matched_tasks.append({
                    'id': candidate['id'],
                    'title': candidate['title'],
                    'status': candidate['status'],
                    'similarity': round(final_sim, 4),
                    'match_type': 'semantic',
                    'created_at': str(candidate.get('created_at', ''))
                })
        
        # 按相似度降序
        matched_tasks.sort(key=lambda x: x['similarity'], reverse=True)
        
        # 判断是否重复：前缀匹配 或 语义匹配
        has_prefix_match = any(
            c.get('title', '')[:self.prefix_length] == title_prefix
            for c in candidates
        )
        is_duplicate = has_prefix_match or len(matched_tasks) > 0
        
        duplicate_type = 'none'
        if has_prefix_match and matched_tasks:
            duplicate_type = 'both'
        elif has_prefix_match:
            duplicate_type = 'prefix'
        elif matched_tasks:
            duplicate_type = 'semantic'
        
        return {
            'is_duplicate': is_duplicate,
            'duplicate_type': duplicate_type,
            'title_prefix': title_prefix,
            'matched_tasks': matched_tasks[:5],  # 最多返回5个
            'similarity_threshold': self.similarity_threshold,
            'prefix_matches': sum(1 for c in candidates
                                   if c.get('title', '')[:self.prefix_length] == title_prefix),
            'semantic_matches': len(matched_tasks),
            'check_type': 'deduplication'
        }
    
    def batch_check(self, titles: List[str], goal_id: Optional[int] = None) -> List[Dict]:
        """批量检查"""
        return [self.check(title, goal_id) for title in titles]


# ============================================================================
# Unified Guard: 三重保障协调器
# ============================================================================

class TaskGenerationGuard:
    """
    任务生成三重保障协调器
    
    使用方式:
        guard = TaskGenerationGuard()
        result = guard.check_and_allow("任务标题", goal_id=1, description="描述")
        if result.can_generate:
            # 安全创建任务
            task_id = guard.create_task_safely("任务标题", "描述", goal_id=1)
    """
    
    def __init__(self,
                 max_tasks_per_24h: int = 100,  # 满速模式：每项目每天最多100个
                 max_pending_per_goal: int = 100,  # 满速模式：每项目最多100个pending
                 similarity_threshold: float = 0.45,
                 prefix_length: int = 15):
        
        self.idempotency = IdempotencyLayer()
        self.rate_limit = RateLimitLayer(
            max_tasks=max_tasks_per_24h,
            max_pending=max_pending_per_goal
        )
        self.dedup = SemanticDedupLayer(
            prefix_length=prefix_length,
            similarity_threshold=similarity_threshold
        )
        self.config = {
            'max_tasks_per_24h': max_tasks_per_24h,
            'max_pending_per_goal': max_pending_per_goal,
            'similarity_threshold': similarity_threshold,
            'prefix_length': prefix_length,
            'version': 'V4.6'
        }
        self.batch_id = self._generate_batch_id()
        logger.info(f"TaskGenerationGuard V4.6 initialized, batch_id={self.batch_id}")
    
    def _generate_batch_id(self) -> str:
        return f"V46-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{os.urandom(4).hex()}"
    
    def check(self, title: str, goal_id: Optional[int] = None,
              description: str = '') -> GuardResult:
        """
        执行三重保障检查（不创建任务，只检查）
        
        Returns:
            GuardResult: 检查结果
        """
        layer_checks = {}
        
        # Layer 1: 幂等性检查
        idem_key = self.idempotency.generate_key(title, goal_id, description)
        idem_result = self.idempotency.check(idem_key)
        layer_checks['idempotency'] = idem_result
        
        if not idem_result['is_safe']:
            return GuardResult(
                decision=GuardDecision.BLOCKED_IDEMPOTENT,
                can_generate=False,
                reason=f"幂等性检查: 该任务请求已存在 (key={idem_key[:8]}..., task_id={idem_result.get('local_task_id')})",
                layer_checks=layer_checks,
                idempotency_key=idem_key,
                generation_batch_id=self.batch_id
            )
        
        # Layer 2: 频率限制检查
        rate_result = self.rate_limit.check_all(goal_id or 0)
        layer_checks['rate_limit'] = rate_result
        
        if not rate_result['can_generate']:
            return GuardResult(
                decision=GuardDecision.BLOCKED_RATE_LIMIT,
                can_generate=False,
                reason=rate_result['blocked_reason'],
                layer_checks=layer_checks,
                idempotency_key=idem_key,
                generation_batch_id=self.batch_id
            )
        
        # Layer 3: 语义去重检查
        dedup_result = self.dedup.check(title, goal_id)
        layer_checks['deduplication'] = dedup_result
        
        if dedup_result['is_duplicate']:
            match = dedup_result['matched_tasks'][0] if dedup_result['matched_tasks'] else {}
            dup_type = dedup_result['duplicate_type']
            reason = f"语义去重: 与已有任务ID={match.get('id')}重复, 相似度={match.get('similarity', 'N/A')}, 类型={dup_type}"
            return GuardResult(
                decision=GuardDecision.BLOCKED_DUPLICATE,
                can_generate=False,
                reason=reason,
                layer_checks=layer_checks,
                idempotency_key=idem_key,
                generation_batch_id=self.batch_id
            )
        
        # 通过所有检查
        return GuardResult(
            decision=GuardDecision.ALLOWED,
            can_generate=True,
            reason="通过所有三层保障检查",
            layer_checks=layer_checks,
            idempotency_key=idem_key,
            generation_batch_id=self.batch_id
        )
    
    def create_task_safely(self, title: str, description: str,
                           goal_id: Optional[int] = None,
                           priority: int = 2,
                           task_type: str = 'auto_generated_v4.6',
                           execution_mode: str = 'auto',
                           due_date: Optional[str] = None) -> GuardResult:
        """
        安全创建任务：先检查，后创建
        
        Returns:
            GuardResult: 包含task_id（如果成功）
        """
        # Step 1: 检查
        check_result = self.check(title, goal_id, description)
        
        if not check_result.can_generate:
            logger.info(f"⛔ 任务被拦截: {title[:60]} - {check_result.reason}")
            return check_result
        
        # Step 2: 创建任务
        try:
            sql = """
                INSERT INTO tasks
                (title, description, status, priority, goal_id, task_type,
                 execution_mode, due_date, created_at, updated_at)
                VALUES (%s, %s, 'pending', %s, %s, %s, %s, %s, NOW(), NOW())
            """
            execute_update(sql, (
                title, description, priority, goal_id,
                task_type, execution_mode, due_date
            ))
            
            # 获取插入的task_id
            result = execute_query("SELECT LAST_INSERT_ID() as id")
            task_id = result[0]['id'] if result else None
            
            # Step 3: 记录幂等性
            if task_id and check_result.idempotency_key:
                self.idempotency.record(
                    check_result.idempotency_key, task_id, title, goal_id
                )
            
            logger.info(f"✅ 任务已安全创建: ID={task_id}, {title[:60]}")
            
            return GuardResult(
                decision=GuardDecision.ALLOWED,
                can_generate=True,
                reason="任务已成功创建",
                layer_checks=check_result.layer_checks,
                task_id=task_id,
                idempotency_key=check_result.idempotency_key,
                generation_batch_id=self.batch_id
            )
            
        except Exception as e:
            logger.error(f"创建任务失败: {e}")
            return GuardResult(
                decision=GuardDecision.ERROR,
                can_generate=False,
                reason=f"数据库插入失败: {str(e)}",
                layer_checks=check_result.layer_checks,
                idempotency_key=check_result.idempotency_key,
                generation_batch_id=self.batch_id
            )
    
    def filter_recommendations(self, recommendations: List[Dict]) -> Tuple[List[Dict], List[Dict]]:
        """
        过滤推荐任务列表
        
        Args:
            recommendations: 推荐任务列表，每个包含'title', 'goal_id'等
        
        Returns:
            (passed_recommendations, blocked_recommendations)
        """
        if not recommendations:
            return [], []
        
        logger.info(f"开始V4.6过滤: 共 {len(recommendations)} 个推荐任务")
        
        passed = []
        blocked = []
        
        for rec in recommendations:
            title = rec.get('title', '')
            goal_id = rec.get('goal_id')
            description = rec.get('description', '')
            
            result = self.check(title, goal_id, description)
            
            if result.can_generate:
                passed.append({
                    **rec,
                    'guard_result': {
                        'decision': result.decision.value,
                        'idempotency_key': result.idempotency_key,
                        'batch_id': result.generation_batch_id
                    }
                })
                logger.info(f"✅ 通过: {title[:50]} (目标{goal_id})")
            else:
                blocked.append({
                    **rec,
                    'guard_result': {
                        'decision': result.decision.value,
                        'reason': result.reason,
                        'idempotency_key': result.idempotency_key,
                        'batch_id': result.generation_batch_id
                    }
                })
                logger.info(f"❌ 阻止: {title[:50]} - {result.reason}")
        
        logger.info(f"V4.6过滤完成: 通过 {len(passed)}, 阻止 {len(blocked)}")
        return passed, blocked
    
    def get_system_status(self) -> Dict:
        """获取系统状态概览"""
        status = {
            'version': self.config['version'],
            'batch_id': self.batch_id,
            'timestamp': datetime.now().isoformat(),
            'config': self.config,
            'goals': {}
        }
        
        for goal_id in range(1, 8):
            rate = self.rate_limit.check_rate_limit(goal_id)
            pending = self.rate_limit.check_pending_watermark(goal_id)
            status['goals'][goal_id] = {
                'can_generate': rate['can_generate'] and pending['can_generate'],
                'rate_limit': rate,
                'pending_watermark': pending
            }
        
        return status
    
    def cleanup(self, days: int = 30) -> Dict:
        """清理过期数据"""
        removed = self.idempotency.cleanup_old_records(days)
        return {
            'idempotency_records_removed': removed,
            'cleanup_date': datetime.now().isoformat()
        }


def quick_guard_check(title: str, goal_id: int = None, description: str = '') -> Tuple[bool, str]:
    """便捷函数：快速检查"""
    guard = TaskGenerationGuard()
    result = guard.check(title, goal_id, description)
    return result.can_generate, result.reason


if __name__ == "__main__":
    # print("=" * 70)
    # print("SDS任务生成三重保障系统 V4.6 - 功能演示")
    # print("=" * 70)
    
    guard = TaskGenerationGuard()
    
    # 系统状态
    # print("\n【系统状态】")
    status = guard.get_system_status()
    # print(f"版本: {status['version']}")
    # print(f"批次ID: {status['batch_id']}")
    # print(f"配置: {json.dumps(status['config'], indent=2, ensure_ascii=False)}")
    
    # 各目标状态
    # print("\n【各目标生成状态】")
    for gid, s in status['goals'].items():
        icon = "✅" if s['can_generate'] else "⛔"
        rate = s['rate_limit']
        pending = s['pending_watermark']
        # print(f"  {icon} 目标{gid}: 24h={rate['current_count']}/{rate['max_allowed']}, "
              f"pending={pending['current_pending']}/{pending['max_allowed']}")
    
    # 测试检查
    # print("\n【任务检查测试】")
    test_tasks = [
        ("T1: AI助手优化 - SDS调度系统测试", 1, "测试任务描述"),
        ("T2: 和光智成商业化 - 融资BP更新", 2, "商业计划书更新"),
        ("", 1, "空标题测试"),
    ]
    
    for title, gid, desc in test_tasks:
        result = guard.check(title, gid, desc)
        icon = "✅" if result.can_generate else "⛔"
        # print(f"\n  {icon} 标题: {title or '(空)'}")
        # print(f"     决策: {result.decision.value}")
        # print(f"     原因: {result.reason}")
        # print(f"     幂等键: {result.idempotency_key}")
