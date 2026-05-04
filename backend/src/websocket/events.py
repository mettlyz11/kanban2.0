"""
事件处理器封装 - 所有 Socket.IO 事件处理函数
"""

import logging
from typing import Dict, Any, Optional, Callable
from datetime import datetime

from .connection import (
    add_connection, remove_connection, update_heartbeat,
    get_connection, get_user_connections, is_user_online
)
from .rooms import (
    join_room as _join_room, leave_room as _leave_room,
    leave_all_rooms, make_project_room_name, get_room_members
)
from .presence import (
    update_user_presence, remove_user_presence,
    get_online_users_list, build_online_users_event_data
)
from .locks import (
    acquire_lock, release_lock, release_user_locks,
    get_lock, cleanup_expired_locks
)

logger = logging.getLogger(__name__)

# Socket.IO 实例（由 index.py 注入）
_socketio = None


def set_socketio(socketio_instance):
    """设置 Socket.IO 实例"""
    global _socketio
    _socketio = socketio_instance


def get_socketio():
    """获取 Socket.IO 实例"""
    return _socketio


def emit_event(event: str, data: Dict[str, Any], room: Optional[str] = None, broadcast: bool = False):
    """
    发送事件
    
    Args:
        event: 事件名称
        data: 事件数据
        room: 目标房间（可选）
        broadcast: 是否广播（已废弃，emit 默认即广播）
    """
    if not _socketio:
        logger.warning(f"Socket.IO 未初始化，无法发送事件: {event}")
        return
    
    try:
        if room:
            _socketio.emit(event, data, room=room)
        else:
            _socketio.emit(event, data)
    except Exception as e:
        logger.error(f"发送事件失败: {event}, error={e}")


# ============================================
# 认证事件
# ============================================
def handle_authenticate(socket_id: str, user_id: int, username: str):
    """
    处理认证事件
    
    Args:
        socket_id: Socket.IO session ID
        user_id: 用户 ID
        username: 用户名
    """
    # 添加连接记录
    add_connection(socket_id, user_id, username)
    update_user_presence(user_id, username)
    
    # 发送认证成功事件
    emit_event('authenticated', {
        'success': True,
        'user_id': user_id,
        'username': username,
        'message': '认证成功',
    }, room=socket_id)
    
    # 广播用户上线
    emit_event('user_online', {
        'user_id': user_id,
        'username': username,
        'online_count': len(get_online_users_list()),
    })
    
    # 发送在线用户列表
    emit_event('online_users_list', build_online_users_event_data(), room=socket_id)
    
    logger.info(f"✅ 用户认证成功: user_id={user_id}, username={username}")


# ============================================
# 房间事件
# ============================================
def handle_join_project_room(socket_id: str, data: Dict[str, Any]):
    """
    处理加入项目房间事件
    
    Args:
        socket_id: Socket.IO session ID
        data: 事件数据 {project_id}
    """
    project_id = data.get('project_id')
    if not project_id:
        logger.warning(f"加入房间缺少 project_id: sid={socket_id}")
        return
    
    room_name = make_project_room_name(project_id)
    _join_room(socket_id, room_name)
    
    logger.info(f"🏠 加入项目房间: sid={socket_id}, room={room_name}")


def handle_leave_project_room(socket_id: str, data: Dict[str, Any]):
    """
    处理离开项目房间事件
    
    Args:
        socket_id: Socket.IO session ID
        data: 事件数据 {project_id}
    """
    project_id = data.get('project_id')
    if not project_id:
        return
    
    room_name = make_project_room_name(project_id)
    _leave_room(socket_id, room_name)
    
    logger.info(f"🚪 离开项目房间: sid={socket_id}, room={room_name}")


# ============================================
# 锁事件
# ============================================
def handle_lock_request(socket_id: str, data: Dict[str, Any]):
    """
    处理编辑锁请求
    
    Args:
        socket_id: Socket.IO session ID
        data: 事件数据 {task_id}
    """
    task_id = data.get('task_id')
    if not task_id:
        return
    
    conn_info = get_connection(socket_id)
    if not conn_info:
        logger.warning(f"锁请求: 未找到连接信息 sid={socket_id}")
        return
    
    user_id = conn_info['user_id']
    username = conn_info['username']
    
    success, lock_info = acquire_lock(str(task_id), user_id, username)
    
    if success:
        emit_event('lock_acquired', {
            'task_id': task_id,
            'locked_by': username,
            'expires_at': lock_info['expires_at'],
        }, room=socket_id)
        
        # 广播锁获取（给房间内的其他用户）
        emit_event('lock_acquired', {
            'task_id': task_id,
            'locked_by': username,
            'expires_at': lock_info['expires_at'],
        })
    else:
        emit_event('lock_denied', {
            'task_id': task_id,
            'locked_by': lock_info.get('username'),
            'locked_at': lock_info.get('acquired_at'),
        }, room=socket_id)


def handle_unlock_request(socket_id: str, data: Dict[str, Any]):
    """
    处理编辑锁释放请求
    
    Args:
        socket_id: Socket.IO session ID
        data: 事件数据 {task_id}
    """
    task_id = data.get('task_id')
    if not task_id:
        return
    
    conn_info = get_connection(socket_id)
    if not conn_info:
        return
    
    user_id = conn_info['user_id']
    lock = release_lock(str(task_id), user_id)
    
    if lock:
        emit_event('lock_released', {
            'task_id': task_id,
            'released_by': lock.get('username'),
        })


# ============================================
# 心跳事件
# ============================================
def handle_heartbeat(socket_id: str, data: Dict[str, Any]):
    """
    处理心跳事件
    
    Args:
        socket_id: Socket.IO session ID
        data: 事件数据 {timestamp}
    """
    if update_heartbeat(socket_id):
        emit_event('heartbeat_ack', {
            'timestamp': datetime.now().isoformat(),
        }, room=socket_id)


# ============================================
# 断开连接事件
# ============================================
def handle_disconnect(socket_id: str):
    """
    处理断开连接
    
    Args:
        socket_id: Socket.IO session ID
    """
    conn_info = remove_connection(socket_id)
    if not conn_info:
        return
    
    user_id = conn_info['user_id']
    username = conn_info['username']
    
    # 离开所有房间
    leave_all_rooms(socket_id)
    
    # 释放用户持有的所有锁
    release_user_locks(user_id)
    
    # 如果用户完全离线，广播下线事件
    if not is_user_online(user_id):
        remove_user_presence(user_id)
        
        emit_event('user_offline', {
            'user_id': user_id,
            'username': username,
            'online_count': len(get_online_users_list()),
        })
        
        # 更新所有用户的在线列表
        emit_event('online_users_list', build_online_users_event_data())
    
    logger.info(f"🔌 用户断开: user_id={user_id}, username={username}")


# ============================================
# 任务事件（供业务代码调用）
# ============================================
def emit_task_created(task: Dict[str, Any], created_by: str = '系统'):
    """
    广播任务创建事件
    
    Args:
        task: 任务数据
        created_by: 创建者
    """
    emit_event('task_created', {
        'task': task,
        'created_by': created_by,
    })
    
    # 如果有关联项目，通知项目房间
    project_id = task.get('project_id')
    if project_id:
        room_name = make_project_room_name(project_id)
        emit_event('task_created', {
            'task': task,
            'project_id': project_id,
        }, room=room_name)


def emit_task_updated(task: Dict[str, Any], changes: Dict[str, Any], updated_by: str = '系统'):
    """
    广播任务更新事件
    
    Args:
        task: 任务数据
        changes: 变更内容
        updated_by: 更新者
    """
    emit_event('task_updated', {
        'task': task,
        'changes': changes,
        'updated_by': updated_by,
    })
    
    # 释放编辑锁
    task_id = task.get('id')
    if task_id:
        release_lock(str(task_id))


def emit_task_deleted(task_id, deleted_by: str = '系统'):
    """
    广播任务删除事件
    
    Args:
        task_id: 任务 ID
        deleted_by: 删除者
    """
    emit_event('task_deleted', {
        'task_id': task_id,
        'deleted_by': deleted_by,
    })
    
    # 释放编辑锁
    release_lock(str(task_id))


# ============================================
# 通知事件
# ============================================
def emit_notification(user_id: int, notification: Dict[str, Any]):
    """
    发送通知给指定用户
    
    Args:
        user_id: 用户 ID
        notification: 通知内容
    """
    room_name = f"user:{user_id}"
    emit_event('notification', {
        'user_id': user_id,
        'notification': notification,
        'timestamp': datetime.now().isoformat(),
    }, room=room_name)


def emit_broadcast_notification(notification: Dict[str, Any]):
    """
    广播通知给所有用户
    
    Args:
        notification: 通知内容
    """
    emit_event('notification', {
        'notification': notification,
        'timestamp': datetime.now().isoformat(),
    })
