#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SDS调度系统V4.3升级 - 频率限制与去重机制

【任务#2110】T1: AI助手优化 - 调度系统频率限制与去重机制升级

V4.3核心功能：
1. ✅ 每目标每24小时最多生成2个任务的硬限制
2. ✅ 标题前缀15字精确匹配去重机制
3. ✅ pending任务水位控制（每目标最多3个pending）
4. ✅ 任务生成日志与审计追踪

升级日期: 2026-04-27
版本: V4.3.0
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

# 日志配置
LOG_DIR = Path("/Users/mettlyz/.openclaw/workspace/logs")
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / 'sds-scheduler-v43.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('SchedulerV43')


class DecisionType(Enum):
    """决策类型枚举"""
    ALLOW = "allow"
    BLOCK_RATE_LIMIT = "block_rate_limit"
    BLOCK_PENDING_LIMIT = "block_pending_limit"
    BLOCK_DUPLICATE = "block_duplicate"
    ERROR = "error"


@dataclass
class CheckResult:
    """检查结果"""
    allowed: bool
    decision: DecisionType
    reason: str
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


# ============================================================================
# V4.3 Module 1: 频率限制器 (Rate Limiter)
# ============================================================================

class RateLimiterV43:
    """
    V4.3频率限制器
    
    功能：
    - 每目标(goal_id)每24小时最多生成2个任务（硬限制）
    - 滑动窗口计数，精确到秒
    """
    
    # 配置常量
    MAX_TASKS_PER_24H = 2
    WINDOW_HOURS = 24
    
    def __init__(self, max_tasks: int = None, window_hours: int = None):
        self.max_tasks = max_tasks if max_tasks is not None else self.MAX_TASKS_PER_24H
        self.window_hours = window_hours if window_hours is not None else self.WINDOW_HOURS
        logger.info(f"[V4.3] 频率限制器初始化: {self.max_tasks}任务/{self.window_hours}小时")
    
    def check(self, goal_id: int) -> CheckResult:
        """检查目标是否超出频率限制"""
        window_start = datetime.now() - timedelta(hours=self.window_hours)
        
        try:
            sql = """
                SELECT COUNT(*) as count
                FROM tasks
                WHERE goal_id = %s
                  AND task_type LIKE 'auto_generated%%'
                  AND created_at >= %s
            """
            result = execute_query(sql, (goal_id, window_start))
            current_count = result[0].get('count', 0) if result else 0
            
        except Exception as e:
            logger.error(f"频率限制查询失败: {e}")
            return CheckResult(
                allowed=False,
                decision=DecisionType.ERROR,
                reason=f"数据库查询失败: {str(e)}",
                details={'error': str(e)}
            )
        
        # 构建详细信息
        details = {
            'goal_id': goal_id,
            'current_count': current_count,
            'max_allowed': self.max_tasks,
            'remaining_slots': max(0, self.max_tasks - current_count),
            'window_hours': self.window_hours,
            'window_start': window_start.isoformat()
        }
        
        if current_count < self.max_tasks:
            return CheckResult(
                allowed=True,
                decision=DecisionType.ALLOW,
                reason=f"频率检查通过: 当前{current_count}/{self.max_tasks}",
                details=details
            )
        else:
            return CheckResult(
                allowed=False,
                decision=DecisionType.BLOCK_RATE_LIMIT,
                reason=f"频率限制: 目标{goal_id}过去{self.window_hours}小时已生成{current_count}个任务（上限{self.max_tasks}）",
                details=details
            )
    
    def get_all_status(self) -> Dict[int, Dict]:
        """获取所有目标的频率状态"""
        status = {}
        for goal_id in range(1, 8):
            result = self.check(goal_id)
            status[goal_id] = result.details
        return status


# ============================================================================
# V4.3 Module 2: Pending水位控制器 (Pending Watermark)
# ============================================================================

class PendingWatermarkV43:
    """
    V4.3 Pending任务水位控制器
    
    功能：
    - 每目标(goal_id)最多3个pending任务
    - 防止任务积压
    """
    
    MAX_PENDING_PER_GOAL = 3
    
    def __init__(self, max_pending: int = None):
        self.max_pending = max_pending if max_pending is not None else self.MAX_PENDING_PER_GOAL
        logger.info(f"[V4.3] Pending水位控制器初始化: 上限{self.max_pending}")
    
    def check(self, goal_id: int) -> CheckResult:
        """检查目标pending任务水位"""
        try:
            sql = """
                SELECT COUNT(*) as count
                FROM tasks
                WHERE status = 'pending'
                  AND goal_id = %s
            """
            result = execute_query(sql, (goal_id,))
            current_pending = result[0].get('count', 0) if result else 0
            
        except Exception as e:
            logger.error(f"水位检查查询失败: {e}")
            return CheckResult(
                allowed=False,
                decision=DecisionType.ERROR,
                reason=f"数据库查询失败: {str(e)}",
                details={'error': str(e)}
            )
        
        # 构建详细信息
        details = {
            'goal_id': goal_id,
            'current_pending': current_pending,
            'max_allowed': self.max_pending,
            'available_slots': max(0, self.max_pending - current_pending)
        }
        
        if current_pending < self.max_pending:
            return CheckResult(
                allowed=True,
                decision=DecisionType.ALLOW,
                reason=f"水位检查通过: 当前pending={current_pending}/{self.max_pending}",
                details=details
            )
        else:
            return CheckResult(
                allowed=False,
                decision=DecisionType.BLOCK_PENDING_LIMIT,
                reason=f"水位限制: 目标{goal_id}当前有{current_pending}个pending任务（上限{self.max_pending}）",
                details=details
            )
    
    def get_all_status(self) -> Dict[int, Dict]:
        """获取所有目标的pending水位状态"""
        status = {}
        for goal_id in range(1, 8):
            result = self.check(goal_id)
            status[goal_id] = result.details
        return status


# ============================================================================
# V4.3 Module 3: 标题去重器 (Title Deduplicator)
# ============================================================================

class TitleDeduplicatorV43:
    """
    V4.3标题去重器
    
    功能：
    - 标题前缀15字精确匹配去重
    - Levenshtein距离语义相似度精算
    - 相似度阈值0.85
    """
    
    PREFIX_LENGTH = 15
    SIMILARITY_THRESHOLD = 0.85
    CHECK_STATUSES = ('pending', 'in_progress', 'completed', 'done')
    
    def __init__(self, prefix_length: int = None, similarity_threshold: float = None):
        self.prefix_length = prefix_length if prefix_length is not None else self.PREFIX_LENGTH
        self.similarity_threshold = similarity_threshold if similarity_threshold is not None else self.SIMILARITY_THRESHOLD
        logger.info(f"[V4.3] 标题去重器初始化: 前缀{self.prefix_length}字, 相似度阈值{self.similarity_threshold}")
    
    @staticmethod
    def levenshtein_distance(s1: str, s2: str) -> int:
        """计算Levenshtein编辑距离"""
        if len(s1) < len(s2):
            return TitleDeduplicatorV43.levenshtein_distance(s2, s1)
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
    def calculate_similarity(cls, s1: str, s2: str) -> float:
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
    
    def check_prefix_match(self, title: str, goal_id: Optional[int] = None) -> List[Dict]:
        """第一层：前缀15字精确匹配"""
        if not title:
            return []
        
        prefix = title[:self.prefix_length]
        
        try:
            if goal_id:
                sql = """
                    SELECT id, title, status, goal_id, created_at
                    FROM tasks
                    WHERE LEFT(title, %s) = LEFT(%s, %s)
                      AND goal_id = %s
                      AND status IN %s
                      AND created_at >= NOW() - INTERVAL 7 DAY
                    ORDER BY created_at DESC
                    LIMIT 10
                """
                results = execute_query(sql, (
                    self.prefix_length, title, self.prefix_length,
                    goal_id, self.CHECK_STATUSES
                ))
            else:
                sql = """
                    SELECT id, title, status, goal_id, created_at
                    FROM tasks
                    WHERE LEFT(title, %s) = LEFT(%s, %s)
                      AND status IN %s
                      AND created_at >= NOW() - INTERVAL 7 DAY
                    ORDER BY created_at DESC
                    LIMIT 10
                """
                results = execute_query(sql, (
                    self.prefix_length, title, self.prefix_length,
                    self.CHECK_STATUSES
                ))
            
            return results or []
            
        except Exception as e:
            logger.error(f"前缀匹配查询失败: {e}")
            return []
    
    def check_semantic_match(self, title: str, goal_id: Optional[int] = None) -> List[Dict]:
        """第二层：语义相似度匹配"""
        if not title:
            return []
        
        candidates = []
        
        try:
            if goal_id:
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
            else:
                sql = """
                    SELECT id, title, status, goal_id, created_at
                    FROM tasks
                    WHERE status IN %s
                      AND created_at >= NOW() - INTERVAL 3 DAY
                    ORDER BY created_at DESC
                    LIMIT 100
                """
                results = execute_query(sql, (self.CHECK_STATUSES,))
            
            if not results:
                return []
            
            # 计算每个候选的相似度
            norm_title = self.normalize_text(title)
            
            for cand in results:
                cand_title = cand.get('title', '')
                norm_cand = self.normalize_text(cand_title)
                
                sim1 = self.calculate_similarity(norm_title, norm_cand)
                sim2 = self.calculate_similarity(title, cand_title)
                final_sim = max(sim1, sim2)
                
                if final_sim >= self.similarity_threshold:
                    candidates.append({
                        'id': cand['id'],
                        'title': cand_title,
                        'status': cand['status'],
                        'goal_id': cand.get('goal_id'),
                        'similarity': round(final_sim, 4),
                        'created_at': str(cand.get('created_at', ''))
                    })
            
            # 按相似度降序
            candidates.sort(key=lambda x: x['similarity'], reverse=True)
            return candidates[:5]
            
        except Exception as e:
            logger.error(f"语义匹配查询失败: {e}")
            return []
    
    def check(self, title: str, goal_id: Optional[int] = None) -> CheckResult:
        """综合去重检查"""
        if not title:
            return CheckResult(
                allowed=True,
                decision=DecisionType.ALLOW,
                reason="空标题跳过检查",
                details={'title': ''}
            )
        
        # 第一层：前缀匹配
        prefix_matches = self.check_prefix_match(title, goal_id)
        
        # 第二层：语义匹配
        semantic_matches = self.check_semantic_match(title, goal_id)
        
        # 排除前缀匹配中已存在的
        prefix_ids = {m['id'] for m in prefix_matches}
        semantic_matches = [m for m in semantic_matches if m['id'] not in prefix_ids]
        
        all_matches = prefix_matches + semantic_matches
        
        details = {
            'title_prefix': title[:self.prefix_length],
            'prefix_matches_count': len(prefix_matches),
            'semantic_matches_count': len(semantic_matches),
            'total_matches': len(all_matches),
            'matched_tasks': all_matches[:5],
            'goal_id': goal_id
        }
        
        if len(prefix_matches) > 0:
            match = prefix_matches[0]
            return CheckResult(
                allowed=False,
                decision=DecisionType.BLOCK_DUPLICATE,
                reason=f"前缀匹配: 与任务#{match['id']}标题前缀重复 ('{title[:self.prefix_length]}')",
                details=details
            )
        
        if len(semantic_matches) > 0:
            match = semantic_matches[0]
            return CheckResult(
                allowed=False,
                decision=DecisionType.BLOCK_DUPLICATE,
                reason=f"语义匹配: 与任务#{match['id']}相似度{match['similarity']} (阈值{self.similarity_threshold})",
                details=details
            )
        
        return CheckResult(
            allowed=True,
            decision=DecisionType.ALLOW,
            reason=f"去重检查通过: 前缀匹配{len(prefix_matches)}, 语义匹配{len(semantic_matches)}",
            details=details
        )


# ============================================================================
# V4.3 Module 4: 审计日志 (Audit Logger)
# ============================================================================

class AuditLoggerV43:
    """
    V4.3审计日志器
    
    功能：
    - 记录每次任务生成的完整检查过程
    - 记录决策原因和详细信息
    - JSON格式持久化存储
    """
    
    def __init__(self, log_file: str = None):
        self.log_file = log_file or str(LOG_DIR / 'sds-audit-v43.jsonl')
        self._ensure_log_dir()
        logger.info(f"[V4.3] 审计日志器初始化: {self.log_file}")
    
    def _ensure_log_dir(self):
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
    
    def log(self, event_type: str, title: str, goal_id: int,
            decision: DecisionType, reason: str, details: Dict = None) -> str:
        """记录审计事件"""
        event_id = f"V43-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{os.urandom(4).hex()}"
        
        entry = {
            'event_id': event_id,
            'event_type': event_type,
            'timestamp': datetime.now().isoformat(),
            'version': 'V4.3',
            'task_title': title,
            'goal_id': goal_id,
            'decision': decision.value,
            'reason': reason,
            'details': details or {}
        }
        
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
            logger.info(f"[审计] {event_type} - {decision.value}: {title[:50]}")
        except IOError as e:
            logger.error(f"写入审计日志失败: {e}")
        
        return event_id
    
    def get_recent_logs(self, limit: int = 100) -> List[Dict]:
        """获取最近的审计日志"""
        logs = []
        if not os.path.exists(self.log_file):
            return logs
        
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            for line in lines[-limit:]:
                line = line.strip()
                if line:
                    try:
                        logs.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
            
            return logs
            
        except IOError as e:
            logger.error(f"读取审计日志失败: {e}")
            return logs
    
    def get_statistics(self, hours: int = 24) -> Dict:
        """获取统计信息"""
        logs = self.get_recent_logs(limit=1000)
        cutoff = datetime.now() - timedelta(hours=hours)
        
        stats = {
            'total_events': 0,
            'allowed': 0,
            'blocked': 0,
            'blocked_by_reason': {
                'rate_limit': 0,
                'pending_limit': 0,
                'duplicate': 0
            },
            'per_goal': {}
        }
        
        for log in logs:
            try:
                ts = datetime.fromisoformat(log['timestamp'])
                if ts < cutoff:
                    continue
            except (ValueError, KeyError):
                continue
            
            stats['total_events'] += 1
            
            decision = log.get('decision', '')
            if decision == 'allow':
                stats['allowed'] += 1
            else:
                stats['blocked'] += 1
                if 'rate_limit' in decision:
                    stats['blocked_by_reason']['rate_limit'] += 1
                elif 'pending_limit' in decision:
                    stats['blocked_by_reason']['pending_limit'] += 1
                elif 'duplicate' in decision:
                    stats['blocked_by_reason']['duplicate'] += 1
            
            goal_id = log.get('goal_id')
            if goal_id:
                if goal_id not in stats['per_goal']:
                    stats['per_goal'][goal_id] = {'allowed': 0, 'blocked': 0}
                if decision == 'allow':
                    stats['per_goal'][goal_id]['allowed'] += 1
                else:
                    stats['per_goal'][goal_id]['blocked'] += 1
        
        return stats


# ============================================================================
# V4.3 Main: 统一调度器
# ============================================================================

class SchedulerV43:
    """
    V4.3统一调度器 - 频率限制与去重机制
    
    使用方式:
        scheduler = SchedulerV43()
        result = scheduler.can_generate_task("任务标题", goal_id=1)
        if result.allowed:
            # 创建任务
            scheduler.log_audit("create", "任务标题", goal_id, result.decision, result.reason)
    """
    
    def __init__(self,
                 max_tasks_per_24h: int = 2,
                 max_pending_per_goal: int = 3,
                 prefix_length: int = 15,
                 similarity_threshold: float = 0.85):
        
        # 初始化各个模块
        self.rate_limiter = RateLimiterV43(max_tasks=max_tasks_per_24h)
        self.pending_watermark = PendingWatermarkV43(max_pending=max_pending_per_goal)
        self.deduplicator = TitleDeduplicatorV43(
            prefix_length=prefix_length,
            similarity_threshold=similarity_threshold
        )
        self.audit_logger = AuditLoggerV43()
        
        self.config = {
            'version': 'V4.3',
            'max_tasks_per_24h': max_tasks_per_24h,
            'max_pending_per_goal': max_pending_per_goal,
            'prefix_length': prefix_length,
            'similarity_threshold': similarity_threshold,
            'init_time': datetime.now().isoformat()
        }
        
        logger.info("="*70)
        logger.info("SDS调度系统V4.3初始化完成")
        logger.info("="*70)
        logger.info(f"配置: {json.dumps(self.config, indent=2, ensure_ascii=False)}")
    
    def can_generate_task(self, title: str, goal_id: int) -> CheckResult:
        """
        执行完整检查流程：任务是否可以生成
        
        检查顺序：
        1. 频率限制检查
        2. Pending水位检查
        3. 标题去重检查
        
        Returns:
            CheckResult: 检查结果
        """
        if not title:
            return CheckResult(
                allowed=False,
                decision=DecisionType.ERROR,
                reason="任务标题不能为空",
                details={'title': title, 'goal_id': goal_id}
            )
        
        # Step 1: 频率限制检查
        rate_result = self.rate_limiter.check(goal_id)
        if not rate_result.allowed:
            self.audit_logger.log(
                "pre_check", title, goal_id,
                rate_result.decision, rate_result.reason, rate_result.details
            )
            return rate_result
        
        # Step 2: Pending水位检查
        pending_result = self.pending_watermark.check(goal_id)
        if not pending_result.allowed:
            self.audit_logger.log(
                "pre_check", title, goal_id,
                pending_result.decision, pending_result.reason, pending_result.details
            )
            return pending_result
        
        # Step 3: 标题去重检查
        dedup_result = self.deduplicator.check(title, goal_id)
        if not dedup_result.allowed:
            self.audit_logger.log(
                "pre_check", title, goal_id,
                dedup_result.decision, dedup_result.reason, dedup_result.details
            )
            return dedup_result
        
        # 所有检查通过
        final_details = {
            'rate_check': rate_result.details,
            'pending_check': pending_result.details,
            'dedup_check': dedup_result.details
        }
        
        return CheckResult(
            allowed=True,
            decision=DecisionType.ALLOW,
            reason="所有V4.3检查通过",
            details=final_details
        )
    
    def create_task_safely(self, title: str, description: str,
                           goal_id: int, priority: int = 2,
                           task_type: str = 'auto_generated_v43') -> CheckResult:
        """
        安全创建任务：先检查，后创建
        
        Returns:
            CheckResult: 包含task_id（如果成功创建）
        """
        # 执行检查
        check_result = self.can_generate_task(title, goal_id)
        
        if not check_result.allowed:
            logger.info(f"⛔ 任务被拦截: {title[:60]} - {check_result.reason}")
            return check_result
        
        # 创建任务
        try:
            sql = """
                INSERT INTO tasks
                (title, description, status, priority, goal_id, task_type,
                 execution_mode, created_at, updated_at)
                VALUES (%s, %s, 'pending', %s, %s, %s, 'auto', NOW(), NOW())
            """
            execute_update(sql, (title, description, priority, goal_id, task_type))
            
            # 获取task_id
            result = execute_query("SELECT LAST_INSERT_ID() as id")
            task_id = result[0]['id'] if result else None
            
            # 记录审计日志
            audit_details = {**check_result.details, 'task_id': task_id}
            event_id = self.audit_logger.log(
                "create", title, goal_id,
                check_result.decision, f"任务创建成功: ID={task_id}", audit_details
            )
            
            logger.info(f"✅ 任务已安全创建: ID={task_id}, {title[:60]}")
            
            final_result = CheckResult(
                allowed=True,
                decision=DecisionType.ALLOW,
                reason=f"任务已成功创建, ID={task_id}",
                details={**check_result.details, 'task_id': task_id, 'audit_event_id': event_id}
            )
            
            return final_result
            
        except Exception as e:
            logger.error(f"创建任务失败: {e}")
            error_result = CheckResult(
                allowed=False,
                decision=DecisionType.ERROR,
                reason=f"数据库插入失败: {str(e)}",
                details={'error': str(e), 'title': title, 'goal_id': goal_id}
            )
            self.audit_logger.log(
                "error", title, goal_id,
                error_result.decision, error_result.reason, error_result.details
            )
            return error_result
    
    def get_system_status(self) -> Dict:
        """获取系统状态概览"""
        status = {
            'version': self.config['version'],
            'timestamp': datetime.now().isoformat(),
            'config': self.config,
            'goals': {}
        }
        
        for goal_id in range(1, 8):
            rate = self.rate_limiter.check(goal_id)
            pending = self.pending_watermark.check(goal_id)
            
            status['goals'][goal_id] = {
                'can_generate': rate.allowed and pending.allowed,
                'rate_limit': rate.details,
                'pending_watermark': pending.details
            }
        
        # 添加审计统计
        status['audit_stats'] = self.audit_logger.get_statistics()
        
        return status
    
    def print_status_report(self):
        """打印状态报告"""
        status = self.get_system_status()
        
        print("\n" + "="*70)
        print("  SDS调度系统V4.3状态报告")
        print("="*70)
        print(f"版本: {status['version']}")
        print(f"时间: {status['timestamp']}")
        print()
        print("【各目标生成状态】")
        for gid, s in status['goals'].items():
            icon = "✅" if s['can_generate'] else "⛔"
            rate = s['rate_limit']
            pending = s['pending_watermark']
            print(f"  {icon} 目标{gid}:")
            print(f"     24h生成: {rate['current_count']}/{rate['max_allowed']}")
            print(f"     pending: {pending['current_pending']}/{pending['max_allowed']}")
            print()
        
        print("【审计统计】")
        audit = status['audit_stats']
        print(f"  总检查次数: {audit['total_events']}")
        print(f"  通过: {audit['allowed']}, 拦截: {audit['blocked']}")
        if audit['blocked'] > 0:
            print(f"    - 频率限制拦截: {audit['blocked_by_reason']['rate_limit']}")
            print(f"    - 水位限制拦截: {audit['blocked_by_reason']['pending_limit']}")
            print(f"    - 去重拦截: {audit['blocked_by_reason']['duplicate']}")
        print("="*70)


# ============================================================================
# 便捷函数
# ============================================================================

def quick_check(title: str, goal_id: int) -> Tuple[bool, str]:
    """快速检查任务是否可以生成"""
    scheduler = SchedulerV43()
    result = scheduler.can_generate_task(title, goal_id)
    return result.allowed, result.reason


def safe_create_task(title: str, description: str, goal_id: int, priority: int = 2) -> Optional[int]:
    """便捷函数：安全创建任务"""
    scheduler = SchedulerV43()
    result = scheduler.create_task_safely(title, description, goal_id, priority)
    return result.details.get('task_id') if result.allowed else None


# ============================================================================
# 主程序入口
# ============================================================================

if __name__ == "__main__":
    print("="*70)
    print("  SDS调度系统V4.3 - 频率限制与去重机制升级")
    print("="*70)
    
    scheduler = SchedulerV43()
    
    # 打印系统状态
    scheduler.print_status_report()
    
    # 测试检查
    print("\n【检查测试】")
    test_tasks = [
        ("T1: AI助手优化 - 调度系统V4.3测试", 1),
        ("T2: 和光智成商业化 - 融资BP更新", 2),
        ("T7: 系统维护 - V4.3升级验证", 7),
    ]
    
    for title, gid in test_tasks:
        can_create, reason = quick_check(title, gid)
        icon = "✅" if can_create else "⛔"
        print(f"\n  {icon} 标题: {title}")
        print(f"     目标: {gid}")
        print(f"     结果: {reason}")
