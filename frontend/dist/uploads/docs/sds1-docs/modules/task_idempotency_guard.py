#!/usr/bin/env python3
"""
任务幂等性保障模块 - SDS调度系统优化
功能: 防止同一任务被重复生成和执行
实现: 基于请求指纹 + 状态机的幂等性保障
"""

import os
import sys
import json
import hashlib
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent / 'scripts'))
from lib.db_connector import get_db_connection, execute_query, execute_update


class TaskIdempotencyGuard:
    """任务幂等性保障器
    
    保障机制:
    1. 请求指纹: 根据任务关键信息生成唯一标识
    2. 原子性检查: 先检查再创建，使用数据库事务
    3. 状态追踪: 记录每个请求的处理状态
    4. TTL清理: 过期请求自动清理
    """
    
    STATUS_PENDING = 'pending'
    STATUS_PROCESSING = 'processing'
    STATUS_COMPLETED = 'completed'
    STATUS_FAILED = 'failed'
    STATUS_DUPLICATE = 'duplicate'
    
    def __init__(self, ttl_hours: int = 24):
        self.ttl_hours = ttl_hours
        self._init_table()
    
    def _init_table(self):
        """初始化幂等性表"""
        sql = """
            CREATE TABLE IF NOT EXISTS task_idempotency_keys (
                id INT AUTO_INCREMENT PRIMARY KEY,
                idempotency_key VARCHAR(128) NOT NULL UNIQUE,
                request_fingerprint VARCHAR(64) NOT NULL,
                source VARCHAR(100) DEFAULT 'sds_scheduler',
                status VARCHAR(20) DEFAULT 'pending',
                task_id INT,
                request_data JSON,
                result_data JSON,
                error_message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                expires_at DATETIME NOT NULL,
                INDEX idx_fingerprint (request_fingerprint),
                INDEX idx_status (status),
                INDEX idx_expires (expires_at)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """
        try:
            execute_update(sql, ())
        except Exception as e:
            print(f"[WARN] 表创建可能已存在: {e}")
    
    @staticmethod
    def generate_request_fingerprint(title: str, project_id: int, 
                                      description: str = None, 
                                      extra_data: Dict = None) -> str:
        """生成请求指纹
        
        根据任务关键信息生成唯一标识，相同内容的请求得到相同的指纹
        """
        # 只使用关键信息生成指纹
        fingerprint_data = {
            'title': title.strip(),
            'project_id': project_id,
            'desc_prefix': (description or '')[:200].strip() if description else '',
        }
        
        if extra_data:
            fingerprint_data['extra'] = json.dumps(extra_data, sort_keys=True)
        
        # 排序后序列化，确保相同内容得到相同指纹
        serialized = json.dumps(fingerprint_data, sort_keys=True, ensure_ascii=True)
        return hashlib.sha256(serialized.encode('utf-8')).hexdigest()
    
    @staticmethod
    def generate_idempotency_key() -> str:
        """生成幂等性Key（用于客户端显式指定）"""
        return f"sds-{uuid.uuid4().hex[:24]}"
    
    def check_or_acquire(self, title: str, project_id: int, 
                          description: str = None,
                          idempotency_key: str = None,
                          source: str = 'sds_scheduler',
                          request_data: Dict = None) -> Dict[str, Any]:
        """检查幂等性或获取执行权
        
        Returns:
            acquired: 是否获得执行权
            existing_task: 已存在的任务（如果重复）
            status: 当前状态
            idempotency_key: 使用的幂等性Key
        """
        fingerprint = self.generate_request_fingerprint(title, project_id, description)
        
        # 如果提供了幂等性Key，优先使用
        key = idempotency_key or fingerprint[:64]
        
        # 先检查是否已存在
        check_sql = """
            SELECT ik.*, t.title as task_title, t.status as task_status
            FROM task_idempotency_keys ik
            LEFT JOIN tasks t ON ik.task_id = t.id
            WHERE ik.request_fingerprint = %s
               OR ik.idempotency_key = %s
            ORDER BY ik.created_at DESC
            LIMIT 1
        """
        
        existing = execute_query(check_sql, (fingerprint, key))
        
        if existing:
            record = existing[0]
            
            if record['task_id']:
                # 已有任务创建
                return {
                    'acquired': False,
                    'existing_task': {
                        'id': record['task_id'],
                        'title': record['task_title'],
                        'status': record['task_status']
                    },
                    'status': self.STATUS_DUPLICATE,
                    'idempotency_key': record['idempotency_key'],
                    'reason': '重复请求: 相同任务已创建'
                }
            elif record['status'] == self.STATUS_PROCESSING:
                # 正在处理中
                return {
                    'acquired': False,
                    'existing_task': None,
                    'status': self.STATUS_PROCESSING,
                    'idempotency_key': record['idempotency_key'],
                    'reason': '请求正在处理中'
                }
        
        # 获取执行权: 创建或更新记录
        expires_at = datetime.now() + timedelta(hours=self.ttl_hours)
        
        try:
            # 尝试插入（使用ON DUPLICATE KEY UPDATE保证原子性）
            insert_sql = """
                INSERT INTO task_idempotency_keys
                (idempotency_key, request_fingerprint, source, status, 
                 request_data, expires_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    status = VALUES(status),
                    updated_at = NOW()
            """
            
            execute_update(insert_sql, (
                key,
                fingerprint,
                source,
                self.STATUS_PROCESSING,
                json.dumps(request_data or {}) if request_data else None,
                expires_at
            ))
            
            return {
                'acquired': True,
                'existing_task': None,
                'status': self.STATUS_PROCESSING,
                'idempotency_key': key,
                'reason': '获得执行权'
            }
            
        except Exception as e:
            # 可能是并发冲突，再次检查
            existing = execute_query(check_sql, (fingerprint, key))
            if existing:
                return {
                    'acquired': False,
                    'existing_task': existing[0].get('task_id'),
                    'status': existing[0]['status'],
                    'idempotency_key': key,
                    'reason': f'并发冲突: {e}'
                }
            raise
    
    def mark_completed(self, idempotency_key: str, task_id: int, 
                        result_data: Dict = None) -> bool:
        """标记任务创建完成"""
        sql = """
            UPDATE task_idempotency_keys
            SET status = %s, task_id = %s, result_data = %s, updated_at = NOW()
            WHERE idempotency_key = %s
        """
        
        try:
            execute_update(sql, (
                self.STATUS_COMPLETED,
                task_id,
                json.dumps(result_data or {}) if result_data else None,
                idempotency_key
            ))
            return True
        except Exception as e:
            print(f"[ERROR] 标记完成失败: {e}")
            return False
    
    def mark_failed(self, idempotency_key: str, error_message: str) -> bool:
        """标记任务创建失败"""
        sql = """
            UPDATE task_idempotency_keys
            SET status = %s, error_message = %s, updated_at = NOW()
            WHERE idempotency_key = %s
        """
        
        try:
            execute_update(sql, (
                self.STATUS_FAILED,
                error_message,
                idempotency_key
            ))
            return True
        except Exception as e:
            print(f"[ERROR] 标记失败失败: {e}")
            return False
    
    def release_lock(self, idempotency_key: str) -> bool:
        """释放锁（允许重试）"""
        sql = """
            UPDATE task_idempotency_keys
            SET status = %s, updated_at = NOW()
            WHERE idempotency_key = %s AND status = %s
        """
        
        try:
            rows = execute_update(sql, (
                self.STATUS_PENDING,
                idempotency_key,
                self.STATUS_PROCESSING
            ))
            return rows > 0
        except Exception as e:
            print(f"[ERROR] 释放锁失败: {e}")
            return False
    
    def cleanup_expired(self) -> int:
        """清理过期记录"""
        sql = "DELETE FROM task_idempotency_keys WHERE expires_at < NOW()"
        return execute_update(sql, ())
    
    def get_stats(self) -> Dict[str, int]:
        """获取统计信息"""
        sql = """
            SELECT status, COUNT(*) as count
            FROM task_idempotency_keys
            GROUP BY status
        """
        results = execute_query(sql, ())
        
        stats = {
            self.STATUS_PENDING: 0,
            self.STATUS_PROCESSING: 0,
            self.STATUS_COMPLETED: 0,
            self.STATUS_FAILED: 0,
            'total': 0
        }
        
        for r in results:
            stats[r['status']] = r['count']
            stats['total'] += r['count']
        
        return stats


# 集成三层保障的便捷函数
def create_task_with_guarantees(title: str, project_id: int, 
                                  description: str = '',
                                  priority: str = 'medium',
                                  status: str = 'pending',
                                  idempotency_key: str = None,
                                  source: str = 'sds_scheduler') -> Dict[str, Any]:
    """创建任务 - 集成三层保障机制
    
    1. 幂等性检查
    2. 频率限制检查
    3. 语义去重检查
    
    Returns:
        success: 是否成功
        task_id: 任务ID（成功时）
        reason: 原因
        checks: 各层检查结果
    """
    from task_frequency_limiter import TaskFrequencyLimiter
    from task_semantic_deduplicator import TaskSemanticDeduplicator
    
    checks = {}
    
    # 第1层: 幂等性检查
    idempotency = TaskIdempotencyGuard()
    idemp_result = idempotency.check_or_acquire(
        title=title,
        project_id=project_id,
        description=description,
        idempotency_key=idempotency_key,
        source=source
    )
    checks['idempotency'] = idemp_result
    
    if not idemp_result['acquired']:
        idempotency.mark_failed(idemp_result['idempotency_key'], idemp_result['reason'])
        return {
            'success': False,
            'task_id': None,
            'reason': f"幂等性拦截: {idemp_result['reason']}",
            'checks': checks
        }
    
    # 第2层: 频率限制检查
    limiter = TaskFrequencyLimiter()
    quota = limiter.get_remaining_quota(project_id)
    checks['frequency'] = quota
    
    if not quota['can_generate']:
        reason = f"频率限制: 项目{project_id}24小时内已生成{quota['used']}个任务"
        idempotency.mark_failed(idemp_result['idempotency_key'], reason)
        idempotency.release_lock(idemp_result['idempotency_key'])
        return {
            'success': False,
            'task_id': None,
            'reason': reason,
            'checks': checks
        }
    
    # 第3层: 语义去重检查
    dedup = TaskSemanticDeduplicator()
    dup_result = dedup.check_duplicate(title, project_id)
    checks['deduplication'] = dup_result
    
    if dup_result['is_duplicate']:
        dup_task = dup_result['duplicate_tasks'][0]
        reason = f"重复检测: 与任务#{dup_task['id']}相似({dup_result['max_similarity']:.2f})"
        idempotency.mark_failed(idemp_result['idempotency_key'], reason)
        idempotency.release_lock(idemp_result['idempotency_key'])
        return {
            'success': False,
            'task_id': None,
            'reason': reason,
            'checks': checks
        }
    
    # 创建任务
    try:
        create_sql = """
            INSERT INTO tasks (project_id, title, description, status, priority, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, NOW(), NOW())
        """
        
        task_id = execute_update(create_sql, (
            project_id, title, description, status, priority
        ), return_last_id=True)
        
        # 更新各保障模块记录
        limiter.record_task_generation(project_id, task_id, title)
        dedup.register_task(task_id, title)
        idempotency.mark_completed(idemp_result['idempotency_key'], task_id)
        
        return {
            'success': True,
            'task_id': task_id,
            'reason': '任务创建成功',
            'checks': checks
        }
        
    except Exception as e:
        error_msg = f"任务创建失败: {e}"
        idempotency.mark_failed(idemp_result['idempotency_key'], error_msg)
        idempotency.release_lock(idemp_result['idempotency_key'])
        raise


if __name__ == '__main__':
    guard = TaskIdempotencyGuard()
    print("幂等性保障模块加载成功")
    
    stats = guard.get_stats()
    print(f"\n当前统计:")
    print(f"  总计: {stats['total']}")
    print(f"  已完成: {stats[guard.STATUS_COMPLETED]}")
    print(f"  处理中: {stats[guard.STATUS_PROCESSING]}")
    print(f"  失败: {stats[guard.STATUS_FAILED]}")
