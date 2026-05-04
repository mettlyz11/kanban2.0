"""
Socket.IO 初始化 - attach 到 Flask HTTP server
"""

import os
import logging
from typing import Optional

from flask import Flask
from flask_socketio import SocketIO

from .auth import authenticate_socket_connection
from .events import (
    set_socketio, handle_authenticate, handle_join_project_room,
    handle_leave_project_room, handle_lock_request, handle_unlock_request,
    handle_heartbeat, handle_disconnect
)
from .heartbeat import start_heartbeat_monitor, stop_heartbeat_monitor
from .presence import build_online_users_event_data
from .locks import cleanup_expired_locks

logger = logging.getLogger(__name__)

# Socket.IO 实例
socketio: Optional[SocketIO] = None


def init_socketio(app: Flask, cors_allowed_origins: str = "*") -> SocketIO:
    """
    初始化 Socket.IO 并 attach 到 Flask app
    
    Args:
        app: Flask 应用实例
        cors_allowed_origins: CORS 允许的源
        
    Returns:
        SocketIO 实例
    """
    global socketio
    
    socketio = SocketIO(
        app,
        cors_allowed_origins=cors_allowed_origins,
        async_mode='eventlet',
        ping_timeout=60,
        ping_interval=25,
        max_http_buffer_size=1e8,
        path='/socket.io',
        logger=False,
        engineio_logger=False,
    )
    
    # 注入 Socket.IO 实例到事件模块
    set_socketio(socketio)
    
    # 注册事件处理器
    _register_handlers(socketio)
    
    # 启动心跳监控
    start_heartbeat_monitor(on_expired=_on_connection_expired)
    
    logger.info("✅ Socket.IO 已初始化并 attach 到 Flask")
    return socketio


def _register_handlers(sio: SocketIO):
    """注册所有 Socket.IO 事件处理器"""
    
    @sio.on('connect')
    def on_connect():
        """处理连接"""
        from flask import request
        sid = request.sid
        logger.debug(f"🔌 新连接: sid={sid}")
    
    @sio.on('disconnect')
    def on_disconnect():
        """处理断开连接"""
        from flask import request
        sid = request.sid
        handle_disconnect(sid)
    
    @sio.on('authenticate')
    def on_authenticate(data):
        """处理认证"""
        from flask import request
        sid = request.sid
        
        # 尝试从 authenticate 事件数据获取用户信息
        user_id = data.get('user_id')
        username = data.get('username', 'unknown')
        
        # 如果没有 user_id，尝试从 query string 认证
        if not user_id:
            success, user = authenticate_socket_connection(request.environ)
            if success and user:
                user_id = user['id']
                username = user['username']
            else:
                # 认证失败，断开连接
                logger.warning(f"❌ 认证失败: sid={sid}")
                sio.emit('authenticated', {
                    'success': False,
                    'message': '认证失败，请提供有效的 token',
                }, room=sid)
                return
        
        handle_authenticate(sid, int(user_id), username)
    
    @sio.on('join_project_room')
    def on_join_project_room(data):
        """处理加入项目房间"""
        from flask import request
        handle_join_project_room(request.sid, data)
    
    @sio.on('leave_project_room')
    def on_leave_project_room(data):
        """处理离开项目房间"""
        from flask import request
        handle_leave_project_room(request.sid, data)
    
    @sio.on('lock_request')
    def on_lock_request(data):
        """处理锁请求"""
        from flask import request
        handle_lock_request(request.sid, data)
    
    @sio.on('unlock_request')
    def on_unlock_request(data):
        """处理锁释放"""
        from flask import request
        handle_unlock_request(request.sid, data)
    
    @sio.on('heartbeat')
    def on_heartbeat(data):
        """处理心跳"""
        from flask import request
        handle_heartbeat(request.sid, data)
    
    logger.info("✅ Socket.IO 事件处理器已注册")


def _on_connection_expired(socket_id: str, conn_info: dict):
    """连接过期回调"""
    # 广播用户下线
    user_id = conn_info.get('user_id')
    username = conn_info.get('username')
    
    if user_id and not _is_user_online(user_id):
        socketio.emit('user_offline', {
            'user_id': user_id,
            'username': username,
            'online_count': 0,
        })
        
        socketio.emit('online_users_list', build_online_users_event_data())


def _is_user_online(user_id: int) -> bool:
    """检查用户是否在线"""
    from .connection import is_user_online as _check
    return _check(user_id)


def get_socketio_instance() -> Optional[SocketIO]:
    """获取 Socket.IO 实例"""
    return socketio


def shutdown_socketio():
    """关闭 Socket.IO"""
    stop_heartbeat_monitor()
    cleanup_expired_locks()
    logger.info("✅ Socket.IO 已关闭")
