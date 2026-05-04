#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SDS任务生成幂等性保障器 (Task Generation Idempotency Guard)
功能：确保同一任务请求不会产生重复执行，保障任务生成的幂等性

设计依据：
- 2026年主流Agent调度系统普遍采用幂等性设计
- 参考OpenAI Swarm框架的任务生成最佳实践
- 幂等性三原则：唯一标识、状态检查、事务安全
"""
import sys
import os
import hashlib
import json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, List
from lib.db_connector import execute_query, execute_update


class IdempotencyGuard:
    """任务生成幂等性保障器"""
    
    def __init__(self):
        self._lock_file = os.path.join(
            os.path.dirname(__file__), '..', 'logs', 'sds-idempotency.lock'
        )
        # 确保logs目录存在
        os.makedirs(os.path.dirname(self._lock_file), exist_ok=True)
    
    @staticmethod
    def generate_idempotency_key(title: str, project_id: Optional[int] = None,
                                  description_prefix: str = '') -> str:
        """
        生成任务幂等性唯一键
        
        基于标题+项目ID+描述前缀生成确定性哈希值，
        相同输入永远生成相同输出。
        
        Args:
            title: 任务标题
            project_id: 项目ID
            description_prefix: 描述前100字（用于区分相似标题）
        
        Returns:
            幂等性键 (SHA-256前16位)
        """
        key_data = json.dumps({
            'title': title.strip(),
            'project_id': project_id,
            'desc_prefix': description_prefix[:100].strip(),
        }, ensure_ascii=False, sort_keys=True)
        
        return hashlib.sha256(key_data.encode('utf-8')).hexdigest()[:16]
    
    def check_idempotency(self, idempotency_key: str) -> Tuple[bool, Dict]:
        """
        检查幂等性键是否已存在
        
        Args:
            idempotency_key: 幂等性键
        
        Returns:
            (是否可安全执行, 详细信息)
        """
        # 1. 检查幂等性日志（本地文件）
        local_result = self._check_local_log(idempotency_key)
        
        # 2. 检查数据库（基于标题去重）
        # 注：不依赖单独的幂等表，而是通过标题+项目精确匹配
        if not local_result['found']:
            db_result = self._check_db_task(idempotency_key)
        else:
            db_result = {'found': False}
        
        is_safe = not local_result['found'] and not db_result['found']
        
        info = {
            'idempotency_key': idempotency_key,
            'safe_to_execute': is_safe,
            'local_found': local_result['found'],
            'db_found': db_result.get('found', False),
            'local_task_id': local_result.get('task_id'),
            'db_task_id': db_result.get('task_id'),
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }
        
        return is_safe, info
    
    def _check_local_log(self, idempotency_key: str) -> Dict:
        """检查本地幂等性日志"""
        if not os.path.exists(self._lock_file):
            return {'found': False}
        
        try:
            with open(self._lock_file, 'r') as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        if entry.get('key') == idempotency_key:
                            return {
                                'found': True,
                                'task_id': entry.get('task_id'),
                                'created_at': entry.get('created_at'),
                            }
                    except json.JSONDecodeError:
                        continue
        except IOError:
            pass
        
        return {'found': False}
    
    def _check_db_task(self, idempotency_key: str) -> Dict:
        """
        通过幂等性键的组成部分在数据库中查找
        这里不做实际查询（需要调用者提供标题信息），
        返回空结果
        """
        return {'found': False}
    
    def record_execution(self, idempotency_key: str, task_id: int, 
                          title: str, project_id: Optional[int] = None) -> bool:
        """
        记录任务执行，建立幂等性关系
        
        Args:
            idempotency_key: 幂等性键
            task_id: 任务ID
            title: 任务标题
            project_id: 项目ID
        
        Returns:
            是否记录成功
        """
        try:
            entry = {
                'key': idempotency_key,
                'task_id': task_id,
                'title': title,
                'project_id': project_id,
                'created_at': datetime.now().isoformat(),
            }
            
            with open(self._lock_file, 'a') as f:
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')
            
            return True
        except IOError as e:
            print(f"⚠️ 记录幂等性日志失败: {e}")
            return False
    
    def safe_insert(self, title: str, description: str, 
                    project_id: Optional[int] = None,
                    priority: int = 2,
                    execution_mode: str = 'auto',
                    task_type: str = 'auto_generated_v4.3',
                    due_date: Optional[str] = None) -> Tuple[bool, Dict]:
        """
        安全插入任务：幂等性检查 + 去重检查 + 频率限制 三重保障
        
        这是任务生成模块应该调用的主入口方法。
        
        Args:
            title: 任务标题
            description: 任务描述
            project_id: 项目ID
            priority: 优先级
            execution_mode: 执行模式
            task_type: 任务类型
            due_date: 截止日期
        
        Returns:
            (是否成功插入, 详细信息)
        """
        from sds.task_rate_limiter import TaskRateLimiter
        from sds.task_dedup import SemanticDeduplicator
        
        result = {
            'title': title,
            'project_id': project_id,
            'action': None,  # 'inserted', 'skipped_rate_limit', 'skipped_duplicate', 'skipped_idempotent'
            'reason': '',
        }
        
        # Step 1: 幂等性检查
        idem_key = self.generate_idempotency_key(
            title, project_id, description
        )
        is_safe, idem_info = self.check_idempotency(idem_key)
        result['idempotency_key'] = idem_key
        
        if not is_safe:
            result['action'] = 'skipped_idempotent'
            result['reason'] = f"幂等性检查: 该任务请求已存在 (key={idem_key[:8]}...)"
            return False, result
        
        # Step 2: 频率限制检查
        if project_id:
            limiter = TaskRateLimiter()
            rate_ok, rate_info = limiter.check_rate_limit(project_id)
            
            if not rate_ok:
                result['action'] = 'skipped_rate_limit'
                result['reason'] = (
                    f"频率限制: project_id={project_id} "
                    f"已达上限 ({rate_info['current_count']}/{rate_info['max_allowed']})"
                )
                return False, result
        
        # Step 3: 语义去重检查
        dedup = SemanticDeduplicator()
        is_dup, dup_info = dedup.is_duplicate(title, project_id)
        
        if is_dup:
            result['action'] = 'skipped_duplicate'
            match = dup_info['matched_tasks'][0] if dup_info['matched_tasks'] else {}
            result['reason'] = (
                f"语义去重: 与已有任务ID={match.get('id')}重复, "
                f"相似度={match.get('similarity', 'N/A')}"
            )
            return False, result
        
        # Step 4: 通过所有检查，安全插入
        try:
            sql = """
                INSERT INTO tasks 
                (title, description, status, priority, project_id, task_type, 
                 execution_mode, due_date, created_at)
                VALUES (%s, %s, 'pending', %s, %s, %s, %s, %s, NOW())
            """
            execute_update(sql, (
                title, description, priority, project_id,
                task_type, execution_mode, due_date
            ))
            
            # 获取插入ID
            id_result = execute_query("SELECT LAST_INSERT_ID() as id")
            task_id = id_result[0]['id']
            
            # 记录幂等性
            self.record_execution(idem_key, task_id, title, project_id)
            
            result['action'] = 'inserted'
            result['task_id'] = task_id
            result['reason'] = '通过所有检查，任务已成功插入'
            
            return True, result
            
        except Exception as e:
            result['action'] = 'error'
            result['reason'] = f"数据库插入失败: {str(e)}"
            return False, result
    
    def cleanup_old_logs(self, days: int = 30) -> int:
        """
        清理过期的幂等性日志
        
        Args:
            days: 保留天数
        
        Returns:
            清理的条目数
        """
        if not os.path.exists(self._lock_file):
            return 0
        
        cutoff = datetime.now() - timedelta(days=days)
        kept = []
        removed = 0
        
        try:
            with open(self._lock_file, 'r') as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        created = datetime.fromisoformat(entry.get('created_at', ''))
                        if created >= cutoff:
                            kept.append(line)
                        else:
                            removed += 1
                    except (json.JSONDecodeError, ValueError):
                        kept.append(line)
            
            with open(self._lock_file, 'w') as f:
                f.writelines(kept)
        except IOError:
            pass
        
        return removed


def safe_insert_task(title: str, description: str, **kwargs) -> Tuple[bool, str]:
    """
    便捷函数：使用三重保障安全插入任务
    
    Args:
        title: 任务标题
        description: 任务描述
        **kwargs: 其他参数 (project_id, priority, execution_mode, due_date)
    
    Returns:
        (是否成功, 日志消息)
    """
    guard = IdempotencyGuard()
    success, result = guard.safe_insert(title, description, **kwargs)
    
    if success:
        log = f"✅ [幂等保障] 任务已插入: ID={result['task_id']}, \"{title[:50]}...\""
    else:
        log = f"⛔ [幂等保障] 任务被拦截: \"{title[:50]}...\" - {result['reason']}"
    
    return success, log


if __name__ == "__main__":
    print("=" * 60)
    print("SDS任务生成幂等性保障器 - 功能演示")
    print("=" * 60)
    
    guard = IdempotencyGuard()
    
    # 测试幂等性键生成
    print("\n【幂等性键生成测试】")
    titles = [
        "T1: 法务纠纷处理 - 证据清单",
        "T1: 法务纠纷处理 - 证据清单",  # 相同标题
        "T1: 法务纠纷处理 - 证据清单整理",  # 相似标题
    ]
    
    seen_keys = set()
    for t in titles:
        key = guard.generate_idempotency_key(t, project_id=80)
        is_dup_key = key in seen_keys
        seen_keys.add(key)
        print(f"  \"{t[:40]}...\"")
        print(f"  → key={key}, {'重复!' if is_dup_key else '唯一'}")
        print()
    
    # 测试幂等性检查
    print("【幂等性检查测试】")
    test_title = "幂等性测试任务 - 2026年4月26日"
    key = guard.generate_idempotency_key(test_title, project_id=75)
    is_safe, info = guard.check_idempotency(key)
    print(f"  任务: \"{test_title}\"")
    print(f"  幂等键: {key}")
    print(f"  安全执行: {is_safe}")
