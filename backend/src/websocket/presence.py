"""
在线用户列表管理
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from .connection import user_socket_map, connected_sockets, is_user_online

logger = logging.getLogger(__name__)

# 用户在线状态缓存
# user_id -> {username, first_seen, last_seen, sessions}
user_presence_cache: Dict[int, Dict[str, Any]] = {}


def update_user_presence(user_id: int, username: str) -> None:
    """
    更新用户在线状态
    
    Args:
        user_id: 用户 ID
        username: 用户名
    """
    now = datetime.now().isoformat()
    
    if user_id not in user_presence_cache:
        user_presence_cache[user_id] = {
            'user_id': user_id,
            'username': username,
            'first_seen': now,
            'last_seen': now,
            'sessions': 1,
        }
    else:
        user_presence_cache[user_id]['username'] = username
        user_presence_cache[user_id]['last_seen'] = now
        user_presence_cache[user_id]['sessions'] = len(user_socket_map.get(user_id, []))


def remove_user_presence(user_id: int) -> None:
    """
    移除用户在线状态
    
    Args:
        user_id: 用户 ID
    """
    if user_id in user_presence_cache:
        del user_presence_cache[user_id]
        logger.info(f"👤 用户下线: user_id={user_id}")


def get_online_users_list() -> List[Dict[str, Any]]:
    """
    获取在线用户列表（去重）
    
    Returns:
        在线用户列表
    """
    online_users = []
    seen_user_ids = set()
    
    for socket_id, conn_info in connected_sockets.items():
        user_id = conn_info.get('user_id')
        if not user_id or user_id in seen_user_ids:
            continue
        
        seen_user_ids.add(user_id)
        sessions = len(user_socket_map.get(user_id, []))
        
        online_users.append({
            'user_id': user_id,
            'username': conn_info.get('username', 'unknown'),
            'connected_at': conn_info.get('connected_at', ''),
            'sessions': sessions,
        })
    
    # 按用户名排序
    online_users.sort(key=lambda x: x['username'])
    return online_users


def get_user_presence(user_id: int) -> Optional[Dict[str, Any]]:
    """
    获取用户在线状态
    
    Args:
        user_id: 用户 ID
        
    Returns:
        用户在线状态，不在线返回 None
    """
    if not is_user_online(user_id):
        return None
    
    return user_presence_cache.get(user_id)


def get_online_count() -> int:
    """
    获取在线用户数（去重）
    
    Returns:
        在线用户数
    """
    return len(user_socket_map)


def get_total_connections() -> int:
    """
    获取总连接数
    
    Returns:
        总连接数
    """
    return len(connected_sockets)


def cleanup_offline_users() -> int:
    """
    清理已离线用户的缓存
    
    Returns:
        清理的用户数
    """
    offline_user_ids = [
        uid for uid in user_presence_cache
        if not is_user_online(uid)
    ]
    
    for user_id in offline_user_ids:
        del user_presence_cache[user_id]
    
    if offline_user_ids:
        logger.info(f"🧹 清理离线用户缓存: {len(offline_user_ids)} 个用户")
    
    return len(offline_user_ids)


def build_online_users_event_data() -> Dict[str, Any]:
    """
    构建在线用户列表事件数据
    
    Returns:
        事件数据字典
    """
    return {
        'users': get_online_users_list(),
        'count': get_online_count(),
        'total_connections': get_total_connections(),
        'timestamp': datetime.now().isoformat(),
    }
