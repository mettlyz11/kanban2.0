#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SDS调度系统V4.3完整版 - 任务 #2110交付物

核心功能：
1. ✅ 每目标每24小时最多生成2个任务的硬限制
2. ✅ 标题前缀15字精确匹配去重机制
3. ✅ pending任务水位控制（每目标最多3个pending）
4. ✅ 任务生成日志与审计追踪
5. ✅ 语义相似度去重（Levenshtein算法）

依赖：lib.db_connector
"""

import sys
import os
import logging
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict

# 添加路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))
from lib.db_connector import get_db_connection, execute_query, execute_update

# ==================== 日志配置 ====================
LOG_DIR = Path("/Users/mettlyz/.openclaw/workspace/logs")
LOG_DIR.mkdir(exist_ok=True)

logger = logging.getLogger('SDS_V43')
logger.setLevel(logging.INFO)

# 文件处理器
file_handler = logging.FileHandler(LOG_DIR / 'sds-v43-audit.log')
file_handler.setFormatter(logging.Formatter(
    '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s'
))
logger.addHandler(file_handler)

# 控制台处理器
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter(
    '[%(levelname)s] %(message)s'
))
logger.addHandler(console_handler)


# ==================== 数据结构定义 ====================
@dataclass
class TaskGenerationCheckResult:
    """任务生成检查结果"""
    can_generate: bool
    goal_id: int
    title: str
    rate_limit_passed: bool
    rate_limit_details: Dict
    pending_watermark_passed: bool
    pending_watermark_details: Dict
    deduplication_passed: bool
    deduplication_details: Dict
    final_decision: str
    decision_reason: str
    check_timestamp: str

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class AuditLogEntry:
    """审计日志条目"""
    event_type: str  # task_generated / task_blocked_rate / task_blocked_pending / task_blocked_dup
    goal_id: int
    task_title: str
    task_id: Optional[int]
    details: Dict[str, Any]
    timestamp: str


# ==================== 1. 频率限制层 ====================
class RateLimitLayer:
    """频率限制层 - 每目标每24小时最多2个任务"""
    
    def __init__(self, max_tasks_per_24h: int = 2, max_pending_per_goal: int = 3,
                 window_hours: int = 24):
        self.max_tasks_per_24h = max_tasks_per_24h
        self.max_pending_per_goal = max_pending_per_goal
        self.window_hours = window_hours
        logger.info(f"[V4.3] 频率限制初始化: 24h上限={max_tasks_per_24h}, pending上限={max_pending_per_goal}")
    
    def check_rate_limit(self, goal_id: int) -> Tuple[bool, Dict]:
        """检查24小时任务生成频率限制"""
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
            logger.warning(f"[RateLimit] DB查询失败 (目标{goal_id}): {e}")
            current_count = 0
        
        can_generate = current_count < self.max_tasks_per_24h
        
        details = {
            'current_count': current_count,
            'max_allowed': self.max_tasks_per_24h,
            'remaining_slots': max(0, self.max_tasks_per_24h - current_count),
            'window_hours': self.window_hours,
            'window_start': window_start.isoformat()
        }
        
        if can_generate:
            logger.debug(f"[RateLimit] 目标{goal_id}: ✓ 通过 ({current_count}/{self.max_tasks_per_24h})")
        else:
            logger.warning(f"[RateLimit] 目标{goal_id}: ✗ 触发限制 ({current_count}/{self.max_tasks_per_24h})")
        
        return can_generate, details
    
    def check_pending_watermark(self, goal_id: int) -> Tuple[bool, Dict]:
        """检查pending任务水位限制（每目标最多3个）"""
        try:
            sql = """
                SELECT COUNT(*) as cnt
                FROM tasks
                WHERE status = 'pending'
                  AND goal_id = %s
            """
            result = execute_query(sql, (goal_id,))
            current_pending = result[0].get('cnt', 0) if result else 0
        except Exception as e:
            logger.warning(f"[Watermark] DB查询失败 (目标{goal_id}): {e}")
            current_pending = 0
        
        can_generate = current_pending < self.max_pending_per_goal
        
        details = {
            'current_pending': current_pending,
            'max_allowed': self.max_pending_per_goal,
            'available_slots': max(0, self.max_pending_per_goal - current_pending)
        }
        
        if can_generate:
            logger.debug(f"[Watermark] 目标{goal_id}: ✓ 通过 ({current_pending}/{self.max_pending_per_goal})")
        else:
            logger.warning(f"[Watermark] 目标{goal_id}: ✗ 触发限制 ({current_pending}/{self.max_pending_per_goal})")
        
        return can_generate, details


# ==================== 2. 去重层 ====================
class DeduplicationLayer:
    """去重层 - 前缀15字匹配 + 语义相似度"""
    
    CHECK_STATUSES = ('pending', 'in_progress', 'completed', 'done')
    
    def __init__(self, prefix_length: int = 15, similarity_threshold: float = 0.85):
        self.prefix_length = prefix_length
        self.similarity_threshold = similarity_threshold
        logger.info(f"[V4.3] 去重初始化: 前缀长度={prefix_length}, 相似度阈值={similarity_threshold}")
    
    @staticmethod
    def levenshtein_distance(s1: str, s2: str) -> int:
        """Levenshtein编辑距离"""
        if len(s1) < len(s2):
            return DeduplicationLayer.levenshtein_distance(s2, s1)
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
        """字符串相似度 (0.0-1.0)"""
        if not s1 and not s2:
            return 1.0
        if not s1 or not s2:
            return 0.0
        max_len = max(len(s1), len(s2))
        distance = cls.levenshtein_distance(s1, s2)
        return 1.0 - (distance / max_len)
    
    @staticmethod
    def normalize_text(text: str) -> str:
        """标准化文本"""
        if not text:
            return ""
        text = text.lower()
        text = re.sub(r'[^\w\u4e00-\u9fff]', '', text)
        return text.strip()
    
    def check_duplicate(self, title: str, goal_id: int = None) -> Tuple[bool, Dict]:
        """
        综合去重检查：
        1. 前缀15字精确匹配
        2. 语义相似度精算
        """
        # 第一层：前缀15字精确匹配
        prefix = title[:self.prefix_length]
        sql = """
            SELECT id, title, status, goal_id, created_at
            FROM tasks
            WHERE title LIKE %s
              AND status IN %s
        """
        params = [prefix + '%', self.CHECK_STATUSES]
        if goal_id:
            sql += " AND goal_id = %s"
            params.append(goal_id)
        sql += " ORDER BY created_at DESC"
        
        prefix_matches = execute_query(sql, tuple(params)) or []
        
        # 如果前缀匹配，直接判定为重复
        if prefix_matches:
            logger.warning(f"[Dedup] 前缀匹配: \"{title[:30]}...\" 匹配到 {len(prefix_matches)} 个任务")
            return False, {
                'is_duplicate': True,
                'match_type': 'prefix',
                'prefix': prefix,
                'matched_tasks': [
                    {
                        'id': m['id'],
                        'title': m['title'],
                        'status': m['status'],
                        'goal_id': m.get('goal_id')
                    } for m in prefix_matches[:3]
                ]
            }
        
        # 第二层：语义相似度精算（扫描近期任务）
        sql2 = """
            SELECT id, title, status, goal_id, created_at
            FROM tasks
            WHERE status IN %s
              AND created_at >= NOW() - INTERVAL 7 DAY
        """
        params2 = [self.CHECK_STATUSES]
        if goal_id:
            sql2 += " AND goal_id = %s"
            params2.append(goal_id)
        sql2 += " ORDER BY created_at DESC LIMIT 50"
        
        recent_tasks = execute_query(sql2, tuple(params2)) or []
        
        norm_new = self.normalize_text(title)
        semantic_matches = []
        
        for task in recent_tasks:
            existing_title = task.get('title', '')
            norm_existing = self.normalize_text(existing_title)
            
            similarity = max(
                self.string_similarity(norm_new, norm_existing),
                self.string_similarity(title, existing_title)
            )
            
            if similarity >= self.similarity_threshold:
                semantic_matches.append({
                    'id': task['id'],
                    'title': task['title'],
                    'status': task['status'],
                    'goal_id': task.get('goal_id'),
                    'similarity': round(similarity, 4)
                })
        
        if semantic_matches:
            logger.warning(f"[Dedup] 语义匹配: \"{title[:30]}...\" 匹配到 {len(semantic_matches)} 个任务")
            return False, {
                'is_duplicate': True,
                'match_type': 'semantic',
                'similarity_threshold': self.similarity_threshold,
                'matched_tasks': sorted(semantic_matches, key=lambda x: x['similarity'], reverse=True)[:3]
            }
        
        # 无重复
        logger.debug(f"[Dedup] ✓ 通过: \"{title[:30]}...\"")
        return True, {
            'is_duplicate': False,
            'match_type': 'none',
            'prefix_check_count': len(prefix_matches),
            'semantic_check_count': len(recent_tasks)
        }


# ==================== 3. 审计日志层 ====================
class AuditLogger:
    """审计日志 - 任务生成全链路追踪"""
    
    def __init__(self):
        self.log_buffer: List[AuditLogEntry] = []
        logger.info("[V4.3] 审计日志已启动")
    
    def log_event(self, event_type: str, goal_id: int, task_title: str,
                  task_id: int = None, details: Dict = None):
        """记录审计事件"""
        entry = AuditLogEntry(
            event_type=event_type,
            goal_id=goal_id,
            task_title=task_title,
            task_id=task_id,
            details=details or {},
            timestamp=datetime.now().isoformat()
        )
        self.log_buffer.append(entry)
        
        # 写入DB持久化
        try:
            sql = """
                INSERT INTO sds_audit_log 
                (event_type, goal_id, task_title, task_id, details, created_at)
                VALUES (%s, %s, %s, %s, %s, NOW())
            """
            details_json = str(details) if details else ''
            execute_update(sql, (event_type, goal_id, task_title, task_id, details_json))
        except Exception as e:
            logger.warning(f"[Audit] DB写入失败: {e}")
    
    def get_stats(self, hours: int = 24) -> Dict:
        """获取审计统计"""
        window_start = datetime.now() - timedelta(hours=hours)
        
        try:
            sql = """
                SELECT
                    event_type,
                    COUNT(*) as count
                FROM sds_audit_log
                WHERE created_at >= %s
                GROUP BY event_type
            """
            results = execute_query(sql, (window_start,)) or []
            
            stats = {
                'period_hours': hours,
                'by_event_type': {r['event_type']: r['count'] for r in results},
                'total_events': sum(r['count'] for r in results)
            }
            return stats
        except Exception as e:
            logger.warning(f"[Audit] 统计查询失败: {e}")
            return {'error': str(e)}


# ==================== 4. 主调度检查器 ====================
class SDSV43Scheduler:
    """SDS V4.3主调度器 - 三层检查机制集成"""
    
    def __init__(self):
        self.rate_limiter = RateLimitLayer(
            max_tasks_per_24h=2,
            max_pending_per_goal=3,
            window_hours=24
        )
        self.deduplicator = DeduplicationLayer(
            prefix_length=15,
            similarity_threshold=0.85
        )
        self.audit_logger = AuditLogger()
        logger.info("=" * 60)
        logger.info("[V4.3] SDS调度系统V4.3初始化完成 ✓")
        logger.info("=" * 60)
    
    def can_generate_task(self, goal_id: int, title: str) -> TaskGenerationCheckResult:
        """
        综合检查：是否可以生成任务
        
        检查顺序：
        1. 频率限制检查
        2. Pending水位检查
        3. 去重检查
        
        Returns:
            TaskGenerationCheckResult: 完整检查结果
        """
        logger.info(f"[Check] 开始检查: 目标{goal_id} - \"{title[:50]}...\"")
        
        # 1. 频率限制检查
        rate_passed, rate_details = self.rate_limiter.check_rate_limit(goal_id)
        if not rate_passed:
            self.audit_logger.log_event(
                'task_blocked_rate', goal_id, title,
                details=rate_details
            )
            return TaskGenerationCheckResult(
                can_generate=False,
                goal_id=goal_id,
                title=title,
                rate_limit_passed=False,
                rate_limit_details=rate_details,
                pending_watermark_passed=None,
                pending_watermark_details=None,
                deduplication_passed=None,
                deduplication_details=None,
                final_decision='blocked_rate_limit',
                decision_reason=f"频率限制: 过去24小时已生成{rate_details['current_count']}个任务",
                check_timestamp=datetime.now().isoformat()
            )
        
        # 2. Pending水位检查
        pending_passed, pending_details = self.rate_limiter.check_pending_watermark(goal_id)
        if not pending_passed:
            self.audit_logger.log_event(
                'task_blocked_pending', goal_id, title,
                details=pending_details
            )
            return TaskGenerationCheckResult(
                can_generate=False,
                goal_id=goal_id,
                title=title,
                rate_limit_passed=True,
                rate_limit_details=rate_details,
                pending_watermark_passed=False,
                pending_watermark_details=pending_details,
                deduplication_passed=None,
                deduplication_details=None,
                final_decision='blocked_pending_watermark',
                decision_reason=f"水位限制: 当前已有{pending_details['current_pending']}个pending任务",
                check_timestamp=datetime.now().isoformat()
            )
        
        # 3. 去重检查
        dup_passed, dup_details = self.deduplicator.check_duplicate(title, goal_id)
        if not dup_passed:
            self.audit_logger.log_event(
                'task_blocked_dup', goal_id, title,
                details=dup_details
            )
            return TaskGenerationCheckResult(
                can_generate=False,
                goal_id=goal_id,
                title=title,
                rate_limit_passed=True,
                rate_limit_details=rate_details,
                pending_watermark_passed=True,
                pending_watermark_details=pending_details,
                deduplication_passed=False,
                deduplication_details=dup_details,
                final_decision='blocked_duplicate',
                decision_reason=f"去重限制: 发现{dup_details['match_type']}匹配的重复任务",
                check_timestamp=datetime.now().isoformat()
            )
        
        # 所有检查通过
        self.audit_logger.log_event(
            'task_allowed', goal_id, title,
            details={'rate': rate_details, 'pending': pending_details}
        )
        
        return TaskGenerationCheckResult(
            can_generate=True,
            goal_id=goal_id,
            title=title,
            rate_limit_passed=True,
            rate_limit_details=rate_details,
            pending_watermark_passed=True,
            pending_watermark_details=pending_details,
            deduplication_passed=True,
            deduplication_details=dup_details,
            final_decision='allowed',
            decision_reason='所有检查通过',
            check_timestamp=datetime.now().isoformat()
        )
    
    def get_system_status(self) -> Dict:
        """获取系统整体状态"""
        status = {
            'version': 'V4.3',
            'timestamp': datetime.now().isoformat(),
            'goals': {},
            'audit_stats': self.audit_logger.get_stats(24)
        }
        
        # 各目标状态
        for goal_id in range(1, 8):
            rate_passed, rate_details = self.rate_limiter.check_rate_limit(goal_id)
            pending_passed, pending_details = self.rate_limiter.check_pending_watermark(goal_id)
            status['goals'][goal_id] = {
                'rate_limit': rate_details,
                'pending_watermark': pending_details,
                'can_generate_rate': rate_passed,
                'can_generate_pending': pending_passed,
                'can_generate': rate_passed and pending_passed
            }
        
        return status
    
    def print_status_report(self):
        """打印状态报告"""
        status = self.get_system_status()
        
        print("\n" + "=" * 70)
        print("  SDS调度系统V4.3 - 状态报告")
        print("=" * 70)
        
        print(f"\n【各目标生成状态】 (24h上限=2, pending上限=3)")
        for gid, goal_status in sorted(status['goals'].items()):
            rate = goal_status['rate_limit']
            pending = goal_status['pending_watermark']
            rate_icon = "✓" if goal_status['can_generate_rate'] else "✗"
            pending_icon = "✓" if goal_status['can_generate_pending'] else "✗"
            can_icon = "✅ 可生成" if goal_status['can_generate'] else "⛔ 被限制"
            
            print(f"\n  目标{gid} {can_icon}")
            print(f"    频率限制: {rate_icon} 已生成{rate['current_count']}/{rate['max_allowed']}个")
            print(f"    水位限制: {pending_icon} pending {pending['current_pending']}/{pending['max_allowed']}个")
        
        print(f"\n【审计统计】过去24小时")
        for event_type, count in status['audit_stats'].get('by_event_type', {}).items():
            print(f"  {event_type}: {count}次")
        print(f"  总计: {status['audit_stats'].get('total_events', 0)}次")
        
        print("\n" + "=" * 70)


# ==================== 初始化审计日志表 ====================
def init_audit_table():
    """初始化审计日志表"""
    try:
        sql = """
            CREATE TABLE IF NOT EXISTS sds_audit_log (
                id INT AUTO_INCREMENT PRIMARY KEY,
                event_type VARCHAR(50) NOT NULL,
                goal_id INT,
                task_title VARCHAR(500),
                task_id INT,
                details TEXT,
                created_at DATETIME,
                INDEX idx_event_type (event_type),
                INDEX idx_goal_id (goal_id),
                INDEX idx_created_at (created_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
        execute_update(sql)
        logger.info("[V4.3] 审计日志表检查/创建完成 ✓")
    except Exception as e:
        logger.warning(f"[V4.3] 审计日志表创建失败: {e}")


# ==================== 主程序入口 ====================
if __name__ == "__main__":
    import sys
    
    # 初始化审计表
    init_audit_table()
    
    # 创建调度器
    scheduler = SDSV43Scheduler()
    
    if len(sys.argv) > 1 and sys.argv[1] == 'status':
        # 状态报告模式
        scheduler.print_status_report()
    elif len(sys.argv) > 2 and sys.argv[1] == 'check':
        # 单任务检查模式
        goal_id = int(sys.argv[2])
        title = ' '.join(sys.argv[3:]) if len(sys.argv) > 3 else '测试任务'
        result = scheduler.can_generate_task(goal_id, title)
        print(f"\n检查结果: {'✅ 可生成' if result.can_generate else '⛔ 被阻止'}")
        print(f"原因: {result.decision_reason}")
    else:
        # 默认：状态报告
        scheduler.print_status_report()
        print("\n使用方法:")
        print("  python scheduler_v43_complete.py status         # 查看状态报告")
        print("  python scheduler_v43_complete.py check 1 任务标题  # 检查特定任务")
