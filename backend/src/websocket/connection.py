"""
连接/断开处理 - 维护用户映射关系
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# ============================================
# 全局连接状态
# ============================================
# socket_id -> {user_id, username, connected_at, last_heartbeat}
connected_sockets: Dict[str, Dict[str, Any]] = {}

# user_id -> [socket_id1, socket_id2, ...] (支持多端登录)
user_socket_map: Dict[int, list] = {}


def add_connection(socket_id: str, user_id: int, username: str) -> None:
    """
    添加新连接
    
    Args:
        socket_id: Socket.IO session ID
        user_id: 用户 ID
        username: 用户名
    """
    now = datetime.now().isoformat()
    
    connected_sockets[socket_id] = {
        'user_id': user_id,
        'username': username,
        'connected_at': now,
        'last_heartbeat': now,
    }
    
    if user_id not in user_socket_map:
        user_socket_map[user_id] = []
    user_socket_map[user_id].append(socket_id)
    
    logger.info(f"🔌 连接建立: sid={socket_id}, user_id={user_id}, username={username}")


def remove_connection(socket_id: str) -> Optional[Dict[str, Any]]:
    """
    移除连接
    
    Args:
        socket_id: Socket.IO session ID
        
    Returns:
        被移除的连接信息，不存在返回 None
    """
    if socket_id not in connected_sockets:
        return None
    
    conn_info = connected_sockets.pop(socket_id)
    user_id = conn_info['user_id']
    
    # 从用户映射中移除
    if user_id in user_socket_map:
        if socket_id in user_socket_map[user_id]:
            user_socket_map[user_id].remove(socket_id)
        if not user_socket_map[user_id]:
            del user_socket_map[user_id]
    
    logger.info(f"🔌 连接断开: sid={socket_id}, user_id={user_id}")
    return conn_info


def get_connection(socket_id: str) -> Optional[Dict[str, Any]]:
    """
    获取连接信息
    
    Args:
        socket_id: Socket.IO session ID
        
    Returns:
        连接信息字典
    """
    return connected_sockets.get(socket_id)


def get_user_connections(user_id: int) -> list:
    """
    获取用户的所有连接
    
    Args:
        user_id: 用户 ID
        
    Returns:
        socket_id 列表
    """
    return user_socket_map.get(user_id, [])


def is_user_online(user_id: int) -> bool:
    """
    检查用户是否在线
    
    Args:
        user_id: 用户 ID
        
    Returns:
        是否在线
    """
    return user_id in user_socket_map and len(user_socket_map[user_id]) > 0


def update_heartbeat(socket_id: str) -> bool:
    """
    更新连接的心跳时间
    
    Args:
        socket_id: Socket.IO session ID
        
    Returns:
        是否更新成功
    """
    if socket_id in connected_sockets:
        connected_sockets[socket_id]['last_heartbeat'] = datetime.now().isoformat()
        return True
    return False


def get_all_connections() -> Dict[str, Dict[str, Any]]:
    """
    获取所有连接
    
    Returns:
        所有连接信息的副本
    """
    return dict(connected_sockets)


def get_online_user_ids() -> list:
    """
    获取所有在线用户 ID 列表
    
    Returns:
        用户 ID 列表
    """
    return list(user_socket_map.keys())


def cleanup_user_connections(user_id: int) -> int:
    """
    清理用户的所有连接（用于强制下线等场景）
    
    Args:
        user_id: 用户 ID
        
    Returns:
        清理的连接数
    """
    sids = user_socket_map.pop(user_id, [])
    count = 0
    for sid in sids:
        if sid in connected_sockets:
            del connected_sockets[sid]
            count += 1
    
    if count > 0:
        logger.info(f"🧹 清理用户连接: user_id={user_id}, 清理 {count} 个连接")
    
    return count


def get_connection_stats() -> Dict[str, Any]:
    """
    获取连接统计信息
    
    Returns:
        统计信息字典
    """
    return {
        'total_connections': len(connected_sockets),
        'unique_users': len(user_socket_map),
        'users_with_multiple_sessions': sum(
            1 for sids in user_socket_map.values() if len(sids) > 1
        ),
    }
