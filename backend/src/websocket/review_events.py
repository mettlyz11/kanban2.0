"""
Review System Real-time Events Module
Handles review task notifications and approval status updates
"""
from flask_socketio import emit, join_room, leave_room
import logging

logger = logging.getLogger(__name__)

class ReviewEventHandler:
    """Review System Event Handler"""
    
    @staticmethod
    def register_events(socketio):
        """Register review-related events"""
        
        @socketio.on('review_join')
        def handle_review_join(data):
            """User joins review room"""
            user_id = data.get('user_id')
            if user_id:
                room = f'review:{user_id}'
                join_room(room)
                logger.info(f'User joined review room: {room}')
                emit('review_joined', {'status': 'success'})
        
        @socketio.on('review_leave')
        def handle_review_leave(data):
            """User leaves review room"""
            user_id = data.get('user_id')
            if user_id:
                room = f'review:{user_id}'
                leave_room(room)
        
        @socketio.on('review_task_submitted')
        def handle_review_task_submitted(data):
            """New task submitted for review"""
            task_id = data.get('task_id')
            reviewers = data.get('reviewers', [])
            
            logger.info(f'Task {task_id} submitted for review')
            
            # Notify all reviewers
            for reviewer_id in reviewers:
                room = f'review:{reviewer_id}'
                emit('review_task_pending', {
                    'task_id': task_id,
                    'title': data.get('title'),
                    'submitted_by': data.get('submitted_by'),
                    'priority': data.get('priority'),
                    'timestamp': data.get('timestamp')
                }, room=room, broadcast=True)
        
        @socketio.on('review_completed')
        def handle_review_completed(data):
            """Review completed (approved/rejected)"""
            task_id = data.get('task_id')
            result = data.get('result')  # 'approved', 'rejected', 'skipped'
            reviewed_by = data.get('reviewed_by')
            submitter_id = data.get('submitter_id')
            
            logger.info(f'Task {task_id} review completed: {result}')
            
            # Notify the submitter
            if submitter_id:
                room = f'review:{submitter_id}'
                emit('review_result', {
                    'task_id': task_id,
                    'result': result,
                    'reviewed_by': reviewed_by,
                    'feedback': data.get('feedback'),
                    'timestamp': data.get('timestamp')
                }, room=room, broadcast=True)
            
            # Broadcast to project room
            project_id = data.get('project_id')
            if project_id:
                room = f'project:{project_id}'
                emit('task_reviewed', {
                    'task_id': task_id,
                    'status': result,
                    'reviewed_by': reviewed_by
                }, room=room, broadcast=True)
        
        @socketio.on('review_bulk_action')
        def handle_review_bulk_action(data):
            """Bulk review action"""
            task_ids = data.get('task_ids', [])
            action = data.get('action')  # 'approve_all', 'reject_all'
            
            logger.info(f'Bulk review action: {action} for {len(task_ids)} tasks')
            
            # Broadcast to project
            project_id = data.get('project_id')
            if project_id:
                room = f'project:{project_id}'
                emit('review_bulk_completed', {
                    'task_ids': task_ids,
                    'action': action,
                    'completed_by': data.get('user_id')
                }, room=room, broadcast=True)

# Global function to emit review events from API routes
def emit_review_task_pending(task_id, title, submitter_id, reviewers, priority='normal'):
    """Emit review task pending event from API"""
    for reviewer_id in reviewers:
        room = f'review:{reviewer_id}'
        emit('review_task_pending', {
            'task_id': task_id,
            'title': title,
            'submitted_by': submitter_id,
            'priority': priority,
            'timestamp': datetime.now().isoformat()
        }, room=room, broadcast=True)

from datetime import datetime
