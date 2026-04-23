"""
WebSocket 事件处理模块 - 实时数据同步
功能：
1. WebSocket 连接管理
2. 任务状态实时同步
3. 在线用户状态显示
4. 协作编辑锁机制
"""

from flask import request, session
from flask_socketio import emit, join_room, leave_room
from datetime import datetime, timedelta
import logging
import uuid

logger = logging.getLogger(__name__)

# ============================================
# 在线用户管理
# ============================================
online_users = {}  # {sid: {user_id, username, connected_at}}
user_sids = {}  # {user_id: [sid1, sid2, ...]} - 支持同一用户多端登录

# ============================================
# 协作编辑锁管理
# ============================================
edit_locks = {}  # {task_id: {user_id, username, locked_at, expires_at}}
LOCK_TIMEOUT_SECONDS = 300  # 5 分钟自动释放

def get_socketio_instance():
    """延迟导入 SocketIO 实例"""
    from app import socketio
    return socketio

# ============================================
# WebSocket 连接事件
# ============================================
def handle_connect():
    """处理客户端连接"""
    socketio = get_socketio_instance()
    
    # 获取用户信息（从 JWT 或 session）
    user_id = request.args.get('user_id', 'anonymous')
    username = request.args.get('username', '访客')
    
    # 记录在线用户
    sid = request.sid
    online_users[sid] = {
        'user_id': user_id,
        'username': username,
        'connected_at': datetime.now().isoformat()
    }
    
    # 维护用户 SID 映射
    if user_id not in user_sids:
        user_sids[user_id] = []
    user_sids[user_id].append(sid)
    
    # 加入用户个人房间（用于发送私人通知）
    join_room(f'user_{user_id}')
    
    logger.info(f"🔌 用户连接：{username} (user_id={user_id}, sid={sid})")
    
    # 广播用户上线事件
    socketio.emit('user_online', {
        'user_id': user_id,
        'username': username,
        'online_count': len(online_users)
    }, broadcast=True)
    
    # 发送当前在线用户列表给新连接的用户
    emit('online_users_list', {
        'users': get_online_users_list()
    })
    
    return True

def handle_disconnect():
    """处理客户端断开连接"""
    socketio = get_socketio_instance()
    
    sid = request.sid
    if sid in online_users:
        user_info = online_users.pop(sid)
        user_id = user_info['user_id']
        username = user_info['username']
        
        # 从用户 SID 列表中移除
        if user_id in user_sids:
            user_sids[user_id].remove(sid)
            if not user_sids[user_id]:
                del user_sids[user_id]
        
        # 释放该用户持有的所有编辑锁
        release_user_locks(user_id)
        
        logger.info(f"🔌 用户断开：{username} (user_id={user_id}, sid={sid})")
        
        # 如果用户所有连接都断开，广播下线事件
        if user_id not in user_sids:
            socketio.emit('user_offline', {
                'user_id': user_id,
                'username': username,
                'online_count': len(online_users)
            }, broadcast=True)
            
            # 通知所有用户更新在线列表
            socketio.emit('online_users_list', {
                'users': get_online_users_list()
            })

# ============================================
# 任务变更同步
# ============================================
def handle_task_created(data):
    """处理任务创建事件"""
    socketio = get_socketio_instance()
    
    task = data.get('task', {})
    task_id = task.get('id')
    project_id = task.get('project_id')
    
    logger.info(f"📝 任务创建：task_id={task_id}")
    
    # 广播任务创建事件
    socketio.emit('task_created', {
        'task': task,
        'created_by': session.get('username', '系统')
    }, broadcast=True)
    
    # 如果有关联项目，通知项目房间
    if project_id:
        socketio.emit('task_created', {
            'task': task,
            'project_id': project_id
        }, room=f'project_{project_id}')

def handle_task_updated(data):
    """处理任务更新事件"""
    socketio = get_socketio_instance()
    
    task = data.get('task', {})
    task_id = task.get('id')
    changes = data.get('changes', {})
    
    logger.info(f"📝 任务更新：task_id={task_id}, changes={changes}")
    
    # 广播任务更新事件
    socketio.emit('task_updated', {
        'task': task,
        'changes': changes,
        'updated_by': session.get('username', '系统')
    }, broadcast=True)
    
    # 释放编辑锁
    if task_id in edit_locks:
        release_lock(task_id)

def handle_task_deleted(data):
    """处理任务删除事件"""
    socketio = get_socketio_instance()
    
    task_id = data.get('task_id')
    
    logger.info(f"📝 任务删除：task_id={task_id}")
    
    # 广播任务删除事件
    socketio.emit('task_deleted', {
        'task_id': task_id,
        'deleted_by': session.get('username', '系统')
    }, broadcast=True)
    
    # 释放编辑锁
    if task_id in edit_locks:
        release_lock(task_id)

# ============================================
# 协作编辑锁
# ============================================
def handle_lock_request(data):
    """处理编辑锁请求"""
    socketio = get_socketio_instance()
    
    task_id = data.get('task_id')
    user_id = session.get('user_id', 'anonymous')
    username = session.get('username', '访客')
    
    logger.info(f"🔒 锁请求：task_id={task_id}, user={username}")
    
    # 检查锁状态
    if task_id in edit_locks:
        lock = edit_locks[task_id]
        
        # 如果是自己持有的锁，续期
        if lock['user_id'] == user_id:
            lock['expires_at'] = (datetime.now() + timedelta(seconds=LOCK_TIMEOUT_SECONDS)).isoformat()
            emit('lock_acquired', {
                'task_id': task_id,
                'locked_by': username,
                'expires_at': lock['expires_at']
            })
            return
        
        # 如果被其他人持有，拒绝请求
        emit('lock_denied', {
            'task_id': task_id,
            'locked_by': lock['username'],
            'locked_at': lock['locked_at']
        })
        return
    
    # 获取锁
    edit_locks[task_id] = {
        'user_id': user_id,
        'username': username,
        'locked_at': datetime.now().isoformat(),
        'expires_at': (datetime.now() + timedelta(seconds=LOCK_TIMEOUT_SECONDS)).isoformat()
    }
    
    # 广播锁状态
    socketio.emit('lock_acquired', {
        'task_id': task_id,
        'locked_by': username,
        'expires_at': edit_locks[task_id]['expires_at']
    }, broadcast=True)
    
    emit('lock_acquired', {
        'task_id': task_id,
        'locked_by': username,
        'expires_at': edit_locks[task_id]['expires_at']
    })

def handle_unlock_request(data):
    """处理编辑锁释放请求"""
    socketio = get_socketio_instance()
    
    task_id = data.get('task_id')
    
    logger.info(f"🔓 锁释放：task_id={task_id}")
    
    release_lock(task_id)

def release_lock(task_id):
    """释放指定任务的编辑锁"""
    socketio = get_socketio_instance()
    
    if task_id in edit_locks:
        lock = edit_locks.pop(task_id)
        
        # 广播锁释放
        socketio.emit('lock_released', {
            'task_id': task_id,
            'released_by': lock['username']
        }, broadcast=True)

def release_user_locks(user_id):
    """释放用户持有的所有编辑锁"""
    socketio = get_socketio_instance()
    
    locked_tasks = [tid for tid, lock in edit_locks.items() if lock['user_id'] == user_id]
    
    for task_id in locked_tasks:
        lock = edit_locks.pop(task_id)
        logger.info(f"🔓 自动释放锁：task_id={task_id} (用户断开)")
        
        # 广播锁释放
        socketio.emit('lock_released', {
            'task_id': task_id,
            'released_by': lock['username'],
            'reason': 'user_disconnected'
        }, broadcast=True)

def handle_heartbeat(data):
    """处理客户端心跳"""
    socketio = get_socketio_instance()
    
    sid = request.sid
    if sid in online_users:
        # 更新最后活跃时间
        online_users[sid]['last_heartbeat'] = datetime.now().isoformat()
        emit('heartbeat_ack', {'timestamp': datetime.now().isoformat()})

# ============================================
# 房间管理
# ============================================
def handle_join_project_room(data):
    """加入项目房间"""
    project_id = data.get('project_id')
    if project_id:
        join_room(f'project_{project_id}')
        logger.info(f"🏠 加入项目房间：project_{project_id}")

def handle_leave_project_room(data):
    """离开项目房间"""
    project_id = data.get('project_id')
    if project_id:
        leave_room(f'project_{project_id}')
        logger.info(f"🚪 离开项目房间：project_{project_id}")

# ============================================
# 工具函数
# ============================================
def get_online_users_list():
    """获取在线用户列表"""
    # 按 user_id 去重
    unique_users = {}
    for sid, info in online_users.items():
        user_id = info['user_id']
        if user_id not in unique_users:
            unique_users[user_id] = {
                'user_id': user_id,
                'username': info['username'],
                'connected_at': info['connected_at'],
                'sessions': 1
            }
        else:
            unique_users[user_id]['sessions'] += 1
    
    return list(unique_users.values())

def cleanup_expired_locks():
    """清理过期的编辑锁"""
    socketio = get_socketio_instance()
    now = datetime.now()
    
    expired_tasks = []
    for task_id, lock in edit_locks.items():
        expires_at = datetime.fromisoformat(lock['expires_at'])
        if now > expires_at:
            expired_tasks.append(task_id)
    
    for task_id in expired_tasks:
        lock = edit_locks.pop(task_id)
        logger.info(f"🔓 锁超时释放：task_id={task_id}")
        
        socketio.emit('lock_released', {
            'task_id': task_id,
            'released_by': lock['username'],
            'reason': 'timeout'
        }, broadcast=True)

# ============================================
# 注册事件处理器
# ============================================
def register_socket_events(socketio):
    """注册所有 WebSocket 事件处理器"""
    
    @socketio.on('connect')
    def on_connect():
        return handle_connect()
    
    @socketio.on('disconnect')
    def on_disconnect():
        return handle_disconnect()
    
    @socketio.on('task_created')
    def on_task_created(data):
        handle_task_created(data)
    
    @socketio.on('task_updated')
    def on_task_updated(data):
        handle_task_updated(data)
    
    @socketio.on('task_deleted')
    def on_task_deleted(data):
        handle_task_deleted(data)
    
    @socketio.on('lock_request')
    def on_lock_request(data):
        handle_lock_request(data)
    
    @socketio.on('unlock_request')
    def on_unlock_request(data):
        handle_unlock_request(data)
    
    @socketio.on('heartbeat')
    def on_heartbeat(data):
        handle_heartbeat(data)
    
    @socketio.on('join_project_room')
    def on_join_project_room(data):
        handle_join_project_room(data)
    
    @socketio.on('leave_project_room')
    def on_leave_project_room(data):
        handle_leave_project_room(data)
    
    logger.info("✅ WebSocket 事件处理器已注册")
