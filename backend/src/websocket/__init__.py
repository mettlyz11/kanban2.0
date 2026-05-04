"""
WebSocket Event Registration
Registers all event handlers for real-time features
"""
from .events import (
    set_socketio, handle_authenticate, handle_join_project_room,
    handle_leave_project_room, handle_lock_request, handle_unlock_request,
    handle_heartbeat, handle_disconnect
)
from .presence import build_online_users_event_data
from .locks import cleanup_expired_locks
from .heartbeat import start_heartbeat_monitor, stop_heartbeat_monitor
from .board_events import BoardEventHandler
from .review_events import ReviewEventHandler
from .meeting_events import MeetingEventHandler
from .calendar_events import CalendarEventHandler
from .sds_events import SDSEventHandler
from .system_events import SystemEventHandler

# Socket.IO instance
socketio = None

def init_socketio(app, cors_allowed_origins="*"):
    """Initialize Socket.IO and attach to Flask app"""
    global socketio
    from flask_socketio import SocketIO
    
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
    
    # Set socketio reference in events module
    set_socketio(socketio)
    
    # Register core event handlers
    from flask import request
    
    @socketio.on('connect')
    def on_connect():
        from flask import request
        print(f"🔌 New connection: sid={request.sid}")
    
    @socketio.on('disconnect')
    def on_disconnect():
        from flask import request
        handle_disconnect(request.sid)
    
    @socketio.on('authenticate')
    def on_authenticate(data):
        from flask import request
        handle_authenticate(request.sid, data)
    
    @socketio.on('join_project_room')
    def on_join_project_room(data):
        from flask import request
        handle_join_project_room(request.sid, data)
    
    @socketio.on('leave_project_room')
    def on_leave_project_room(data):
        from flask import request
        handle_leave_project_room(request.sid, data)
    
    @socketio.on('lock_request')
    def on_lock_request(data):
        from flask import request
        handle_lock_request(request.sid, data)
    
    @socketio.on('unlock_request')
    def on_unlock_request(data):
        from flask import request
        handle_unlock_request(request.sid, data)
    
    @socketio.on('heartbeat')
    def on_heartbeat(data):
        from flask import request
        handle_heartbeat(request.sid, data)
    
    # Register module handlers
    BoardEventHandler.register_events(socketio)
    ReviewEventHandler.register_events(socketio)
    MeetingEventHandler.register_events(socketio)
    CalendarEventHandler.register_events(socketio)
    
    # Start heartbeat monitor
    start_heartbeat_monitor()
    
    print("✅ All WebSocket event handlers registered")
    return socketio

def get_socketio_instance():
    """Get Socket.IO instance"""
    return socketio

def shutdown_socketio():
    """Shutdown Socket.IO"""
    stop_heartbeat_monitor()
    cleanup_expired_locks()
    print("✅ Socket.IO shutdown")
