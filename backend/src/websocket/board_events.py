"""
Kanban Board Real-time Events Module
Handles task drag/drop, column changes and other real-time sync
"""
from flask_socketio import emit, join_room, leave_room
import logging

logger = logging.getLogger(__name__)

class BoardEventHandler:
    """Kanban Board Event Handler"""
    
    @staticmethod
    def register_events(socketio):
        """Register board-related events"""
        
        @socketio.on('board_join')
        def handle_board_join(data):
            """User joins a board room"""
            board_id = data.get('board_id')
            if board_id:
                room = f'board:{board_id}'
                join_room(room)
                logger.info(f'User joined board room: {room}')
                emit('board_joined', {'board_id': board_id, 'status': 'success'})
        
        @socketio.on('board_leave')
        def handle_board_leave(data):
            """User leaves a board room"""
            board_id = data.get('board_id')
            if board_id:
                room = f'board:{board_id}'
                leave_room(room)
                logger.info(f'User left board room: {room}')
        
        @socketio.on('task_moved')
        def handle_task_moved(data):
            """Task moved in kanban board"""
            board_id = data.get('board_id')
            task_id = data.get('task_id')
            from_column = data.get('from_column')
            to_column = data.get('to_column')
            
            logger.info(f'Task moved: {task_id} from {from_column} to {to_column}')
            
            # Broadcast to all users in the board
            room = f'board:{board_id}'
            emit('task_moved', {
                'task_id': task_id,
                'from_column': from_column,
                'to_column': to_column,
                'moved_by': data.get('user_id'),
                'timestamp': data.get('timestamp')
            }, room=room, broadcast=True)
        
        @socketio.on('column_reordered')
        def handle_column_reordered(data):
            """Kanban columns reordered"""
            board_id = data.get('board_id')
            room = f'board:{board_id}'
            emit('column_reordered', {
                'columns': data.get('columns'),
                'reordered_by': data.get('user_id')
            }, room=room, broadcast=True)
        
        @socketio.on('task_drag_started')
        def handle_task_drag_started(data):
            """User starts dragging a task"""
            board_id = data.get('board_id')
            task_id = data.get('task_id')
            room = f'board:{board_id}'
            emit('task_drag_started', {
                'task_id': task_id,
                'user_id': data.get('user_id'),
                'username': data.get('username')
            }, room=room, broadcast=True, include_self=False)
        
        @socketio.on('task_drag_ended')
        def handle_task_drag_ended(data):
            """User ends dragging a task"""
            board_id = data.get('board_id')
            task_id = data.get('task_id')
            room = f'board:{board_id}'
            emit('task_drag_ended', {
                'task_id': task_id,
                'user_id': data.get('user_id')
            }, room=room, broadcast=True, include_self=False)
