"""
心跳检测 - 30秒心跳，清理僵尸连接
"""

import logging
import threading
from datetime import datetime, timedelta
from typing import Callable, Optional

from .connection import connected_sockets, remove_connection

logger = logging.getLogger(__name__)

# 心跳超时时间（秒）
HEARTBEAT_TIMEOUT_SECONDS = 90  # 30秒心跳 * 3 = 90秒超时
HEARTBEAT_CHECK_INTERVAL = 30   # 每30秒检查一次

# 定时器引用
_heartbeat_timer: Optional[threading.Timer] = None
_is_running = False


def check_expired_connections() -> int:
    """
    检查并清理过期连接
    
    Returns:
        清理的连接数
    """
    now = datetime.now()
    expired_sids = []
    
    for socket_id, conn_info in list(connected_sockets.items()):
        last_heartbeat_str = conn_info.get('last_heartbeat')
        if not last_heartbeat_str:
            continue
        
        try:
            # 解析 ISO 格式时间
            last_heartbeat = datetime.fromisoformat(last_heartbeat_str)
            
            # 检查是否超时
            if now - last_heartbeat > timedelta(seconds=HEARTBEAT_TIMEOUT_SECONDS):
                expired_sids.append(socket_id)
        except (ValueError, TypeError) as e:
            logger.warning(f"解析心跳时间失败: sid={socket_id}, error={e}")
            expired_sids.append(socket_id)
    
    # 清理过期连接
    cleaned_count = 0
    for socket_id in expired_sids:
        conn_info = remove_connection(socket_id)
        if conn_info:
            cleaned_count += 1
            logger.info(
                f"💀 清理僵尸连接: sid={socket_id}, "
                f"user_id={conn_info.get('user_id')}, "
                f"username={conn_info.get('username')}"
            )
    
    if cleaned_count > 0:
        logger.info(f"🧹 心跳检测完成: 清理 {cleaned_count} 个僵尸连接")
    
    return cleaned_count


def _heartbeat_loop(
    on_expired: Optional[Callable[[str, dict], None]] = None
) -> None:
    """
    心跳检测循环
    
    Args:
        on_expired: 连接过期时的回调函数 (socket_id, conn_info)
    """
    global _is_running
    
    if not _is_running:
        return
    
    try:
        expired_sids = []
        now = datetime.now()
        
        for socket_id, conn_info in list(connected_sockets.items()):
            last_heartbeat_str = conn_info.get('last_heartbeat')
            if not last_heartbeat_str:
                continue
            
            try:
                last_heartbeat = datetime.fromisoformat(last_heartbeat_str)
                if now - last_heartbeat > timedelta(seconds=HEARTBEAT_TIMEOUT_SECONDS):
                    expired_sids.append((socket_id, conn_info))
            except (ValueError, TypeError):
                expired_sids.append((socket_id, conn_info))
        
        # 清理并触发回调
        for socket_id, conn_info in expired_sids:
            remove_connection(socket_id)
            if on_expired:
                try:
                    on_expired(socket_id, conn_info)
                except Exception as e:
                    logger.error(f"心跳过期回调异常: {e}")
            logger.info(
                f"💀 清理僵尸连接: sid={socket_id}, "
                f"user={conn_info.get('username', 'unknown')}"
            )
        
        if expired_sids:
            logger.info(f"🧹 心跳检测: 清理 {len(expired_sids)} 个僵尸连接")
        
    except Exception as e:
        logger.error(f"心跳检测异常: {e}")
    
    # 安排下一次检测
    if _is_running:
        _schedule_next(on_expired)


def _schedule_next(on_expired: Optional[Callable] = None) -> None:
    """安排下一次心跳检测"""
    global _heartbeat_timer
    _heartbeat_timer = threading.Timer(
        HEARTBEAT_CHECK_INTERVAL,
        _heartbeat_loop,
        args=(on_expired,)
    )
    _heartbeat_timer.daemon = True
    _heartbeat_timer.start()


def start_heartbeat_monitor(
    on_expired: Optional[Callable[[str, dict], None]] = None
) -> None:
    """
    启动心跳监控
    
    Args:
        on_expired: 连接过期时的回调函数
    """
    global _is_running
    
    if _is_running:
        logger.warning("心跳监控已在运行")
        return
    
    _is_running = True
    _schedule_next(on_expired)
    logger.info(f"💓 心跳监控已启动: 间隔={HEARTBEAT_CHECK_INTERVAL}s, 超时={HEARTBEAT_TIMEOUT_SECONDS}s")


def stop_heartbeat_monitor() -> None:
    """停止心跳监控"""
    global _is_running, _heartbeat_timer
    
    _is_running = False
    if _heartbeat_timer:
        _heartbeat_timer.cancel()
        _heartbeat_timer = None
    
    logger.info("💓 心跳监控已停止")


def is_heartbeat_running() -> bool:
    """检查心跳监控是否正在运行"""
    return _is_running
