"""
Meeting Notes Real-time Collaboration Module
Handles real-time collaborative editing and comment sync
"""
from flask_socketio import emit, join_room, leave_room
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

# In-memory store for active editors (in production, use Redis)
active_editors = {}

class MeetingEventHandler:
    """Meeting Notes Event Handler"""
    
    @staticmethod
    def register_events(socketio):
        """Register meeting-related events"""
        
        @socketio.on('meeting_join')
        def handle_meeting_join(data):
            """User joins a meeting room for collaboration"""
            meeting_id = data.get('meeting_id')
            user_id = data.get('user_id')
            username = data.get('username')
            
            if meeting_id:
                room = f'meeting:{meeting_id}'
                join_room(room)
                
                # Track active editors
                if meeting_id not in active_editors:
                    active_editors[meeting_id] = {}
                active_editors[meeting_id][user_id] = {
                    'username': username,
                    'joined_at': datetime.now().isoformat()
                }
                
                logger.info(f'User {username} joined meeting room: {room}')
                
                # Notify others about new editor
                emit('editor_joined', {
                    'user_id': user_id,
                    'username': username,
                    'active_editors': list(active_editors[meeting_id].values())
                }, room=room, broadcast=True, include_self=False)
                
                # Send current editors to new user
                emit('meeting_joined', {
                    'meeting_id': meeting_id,
                    'active_editors': list(active_editors[meeting_id].values()),
                    'status': 'success'
                })
        
        @socketio.on('meeting_leave')
        def handle_meeting_leave(data):
            """User leaves meeting room"""
            meeting_id = data.get('meeting_id')
            user_id = data.get('user_id')
            
            if meeting_id:
                room = f'meeting:{meeting_id}'
                leave_room(room)
                
                # Remove from active editors
                if meeting_id in active_editors and user_id in active_editors[meeting_id]:
                    del active_editors[meeting_id][user_id]
                
                emit('editor_left', {
                    'user_id': user_id,
                    'active_editors': list(active_editors.get(meeting_id, {}).values())
                }, room=room, broadcast=True, include_self=False)
        
        @socketio.on('content_changed')
        def handle_content_changed(data):
            """Real-time content changes from editors"""
            meeting_id = data.get('meeting_id')
            user_id = data.get('user_id')
            changes = data.get('changes')
            
            if meeting_id:
                room = f'meeting:{meeting_id}'
                emit('content_updated', {
                    'user_id': user_id,
                    'changes': changes,
                    'timestamp': datetime.now().isoformat()
                }, room=room, broadcast=True, include_self=False)
        
        @socketio.on('cursor_moved')
        def handle_cursor_moved(data):
            """Cursor position updates"""
            meeting_id = data.get('meeting_id')
            user_id = data.get('user_id')
            position = data.get('position')
            
            if meeting_id:
                room = f'meeting:{meeting_id}'
                emit('cursor_updated', {
                    'user_id': user_id,
                    'username': data.get('username'),
                    'position': position,
                    'selection': data.get('selection')
                }, room=room, broadcast=True, include_self=False)
        
        @socketio.on('comment_added')
        def handle_comment_added(data):
            """New comment on meeting note"""
            meeting_id = data.get('meeting_id')
            comment = data.get('comment')
            
            if meeting_id:
                room = f'meeting:{meeting_id}'
                emit('new_comment', {
                    'comment': comment,
                    'added_by': data.get('user_id'),
                    'timestamp': datetime.now().isoformat()
                }, room=room, broadcast=True)
        
        @socketio.on('save_requested')
        def handle_save_requested(data):
            """Request to save document"""
            meeting_id = data.get('meeting_id')
            user_id = data.get('user_id')
            
            if meeting_id:
                room = f'meeting:{meeting_id}'
                emit('save_status', {
                    'status': 'saving',
                    'requested_by': user_id,
                    'timestamp': datetime.now().isoformat()
                }, room=room, broadcast=True)
