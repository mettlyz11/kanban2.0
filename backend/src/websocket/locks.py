"""
编辑锁管理 - 内存中维护 Map<taskId, {userId, expiresAt}>
锁超时: 30秒
"""

import logging
from typing import Dict, Optional, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# 编辑锁存储
# task_id -> {user_id, username, acquired_at, expires_at}
edit_locks: Dict[str, Dict[str, Any]] = {}

# 锁超时时间（秒）
LOCK_TIMEOUT_SECONDS = 30


def acquire_lock(task_id: str, user_id: int, username: str) -> tuple:
    """
    获取编辑锁
    
    Args:
        task_id: 任务 ID
        user_id: 用户 ID
        username: 用户名
        
    Returns:
        (是否成功, 锁信息字典)
    """
    now = datetime.now()
    
    # 检查是否已有锁
    if task_id in edit_locks:
        existing_lock = edit_locks[task_id]
        expires_at = existing_lock.get('expires_at')
        
        # 检查锁是否已过期
        if expires_at:
            try:
                expires_dt = datetime.fromisoformat(expires_at)
                if now > expires_dt:
                    # 锁已过期，可以获取
                    logger.info(f"🔒 锁已过期，重新获取: task_id={task_id}")
                else:
                    # 锁仍有效
                    if existing_lock.get('user_id') == user_id:
                        # 同一用户，续期
                        existing_lock['expires_at'] = (now + timedelta(seconds=LOCK_TIMEOUT_SECONDS)).isoformat()
                        logger.info(f"🔒 锁续期: task_id={task_id}, user={username}")
                        return True, existing_lock
                    else:
                        # 被其他用户锁定
                        logger.info(f"🔒 锁被拒绝: task_id={task_id}, 已被 {existing_lock.get('username')} 锁定")
                        return False, existing_lock
            except (ValueError, TypeError):
                # 时间格式错误，视为过期
                pass
    
    # 获取新锁
    lock_info = {
        'task_id': task_id,
        'user_id': user_id,
        'username': username,
        'acquired_at': now.isoformat(),
        'expires_at': (now + timedelta(seconds=LOCK_TIMEOUT_SECONDS)).isoformat(),
    }
    edit_locks[task_id] = lock_info
    
    logger.info(f"🔒 锁获取成功: task_id={task_id}, user={username}")
    return True, lock_info


def release_lock(task_id: str, user_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
    """
    释放编辑锁
    
    Args:
        task_id: 任务 ID
        user_id: 用户 ID（可选，用于验证）
        
    Returns:
        被释放的锁信息，不存在返回 None
    """
    if task_id not in edit_locks:
        return None
    
    lock = edit_locks[task_id]
    
    # 验证用户（如果提供了 user_id）
    if user_id is not None and lock.get('user_id') != user_id:
        logger.warning(f"🔓 无权释放锁: task_id={task_id}, requester={user_id}, owner={lock.get('user_id')}")
        return None
    
    del edit_locks[task_id]
    logger.info(f"🔓 锁释放: task_id={task_id}, user={lock.get('username')}")
    return lock


def release_user_locks(user_id: int) -> int:
    """
    释放用户持有的所有锁
    
    Args:
        user_id: 用户 ID
        
    Returns:
        释放的锁数量
    """
    locked_tasks = [
        tid for tid, lock in edit_locks.items()
        if lock.get('user_id') == user_id
    ]
    
    count = 0
    for task_id in locked_tasks:
        lock = edit_locks.pop(task_id)
        count += 1
        logger.info(f"🔓 自动释放锁: task_id={task_id}, user={lock.get('username')}")
    
    return count


def get_lock(task_id: str) -> Optional[Dict[str, Any]]:
    """
    获取锁信息
    
    Args:
        task_id: 任务 ID
        
    Returns:
        锁信息，不存在或已过期返回 None
    """
    if task_id not in edit_locks:
        return None
    
    lock = edit_locks[task_id]
    expires_at = lock.get('expires_at')
    
    if expires_at:
        try:
            expires_dt = datetime.fromisoformat(expires_at)
            if datetime.now() > expires_dt:
                # 锁已过期，清理
                del edit_locks[task_id]
                return None
        except (ValueError, TypeError):
            # 时间格式错误，清理
            del edit_locks[task_id]
            return None
    
    return lock


def is_locked(task_id: str) -> bool:
    """
    检查任务是否被锁定
    
    Args:
        task_id: 任务 ID
        
    Returns:
        是否被锁定
    """
    return get_lock(task_id) is not None


def is_locked_by(task_id: str, user_id: int) -> bool:
    """
    检查任务是否被指定用户锁定
    
    Args:
        task_id: 任务 ID
        user_id: 用户 ID
        
    Returns:
        是否被该用户锁定
    """
    lock = get_lock(task_id)
    if not lock:
        return False
    return lock.get('user_id') == user_id


def cleanup_expired_locks() -> int:
    """
    清理所有过期的锁
    
    Returns:
        清理的锁数量
    """
    now = datetime.now()
    expired_tasks = []
    
    for task_id, lock in list(edit_locks.items()):
        expires_at = lock.get('expires_at')
        if expires_at:
            try:
                expires_dt = datetime.fromisoformat(expires_at)
                if now > expires_dt:
                    expired_tasks.append(task_id)
            except (ValueError, TypeError):
                expired_tasks.append(task_id)
    
    for task_id in expired_tasks:
        lock = edit_locks.pop(task_id)
        logger.info(f"🔓 锁超时释放: task_id={task_id}, user={lock.get('username')}")
    
    if expired_tasks:
        logger.info(f"🧹 清理过期锁: {len(expired_tasks)} 个")
    
    return len(expired_tasks)


def get_all_locks() -> Dict[str, Dict[str, Any]]:
    """
    获取所有锁信息（清理过期锁后）
    
    Returns:
        所有有效锁的字典副本
    """
    cleanup_expired_locks()
    return dict(edit_locks)


def get_lock_stats() -> Dict[str, Any]:
    """
    获取锁统计信息
    
    Returns:
        统计信息字典
    """
    cleanup_expired_locks()
    return {
        'total_locks': len(edit_locks),
        'unique_users': len(set(lock['user_id'] for lock in edit_locks.values())),
    }
