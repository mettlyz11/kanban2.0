"""
SDS (Self-Driving System) Real-time Events Module
Handles task generation, execution status, and system state updates
"""
from flask_socketio import emit
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class SDSEventHandler:
    """SDS Event Handler"""
    
    @staticmethod
    def register_events(socketio):
        """Register SDS-related events"""
        
        @socketio.on('sds_subscribe')
        def handle_sds_subscribe(data):
            """Subscribe to SDS updates"""
            user_id = data.get('user_id')
            if user_id:
                room = f'sds:{user_id}'
                join_room(room)
                emit('sds_subscribed', {'status': 'success'})
        
        @socketio.on('sds_unsubscribe')
        def handle_sds_unsubscribe(data):
            """Unsubscribe from SDS updates"""
            user_id = data.get('user_id')
            if user_id:
                room = f'sds:{user_id}'
                leave_room(room)
    
    @staticmethod
    def emit_task_generated(task, user_id=None):
        """Emit when SDS generates a new task"""
        logger.info(f'SDS task generated: {task.get("id")}')
        
        # Broadcast to all connected users
        emit('sds_task_created', {
            'task': task,
            'generated_at': datetime.now().isoformat(),
            'generated_by': 'SDS'
        }, broadcast=True, namespace='/')
        
        # Also notify specific user if specified
        if user_id:
            room = f'sds:{user_id}'
            emit('sds_task_created', {
                'task': task,
                'generated_at': datetime.now().isoformat()
            }, room=room, broadcast=True)
    
    @staticmethod
    def emit_task_executing(task_id, progress, status_message):
        """Emit task execution progress"""
        logger.info(f'Task {task_id} executing: {progress}%')
        
        emit('sds_task_executing', {
            'task_id': task_id,
            'progress': progress,
            'status_message': status_message,
            'timestamp': datetime.now().isoformat()
        }, broadcast=True, namespace='/')
    
    @staticmethod
    def emit_task_completed(task_id, result_summary):
        """Emit when task execution completes"""
        logger.info(f'Task {task_id} completed')
        
        emit('sds_task_completed', {
            'task_id': task_id,
            'result_summary': result_summary,
            'completed_at': datetime.now().isoformat()
        }, broadcast=True, namespace='/')
    
    @staticmethod
    def emit_task_failed(task_id, error_message):
        """Emit when task execution fails"""
        logger.error(f'Task {task_id} failed: {error_message}')
        
        emit('sds_task_failed', {
            'task_id': task_id,
            'error': error_message,
            'failed_at': datetime.now().isoformat()
        }, broadcast=True, namespace='/')
    
    @staticmethod
    def emit_system_status(status, metrics):
        """Emit SDS system status update"""
        emit('sds_system_status', {
            'status': status,  # 'running', 'paused', 'error'
            'metrics': metrics,
            'timestamp': datetime.now().isoformat()
        }, broadcast=True, namespace='/')
    
    @staticmethod
    def emit_alert(alert_type, message, severity='info'):
        """Emit SDS alert"""
        logger.info(f'SDS alert: [{severity}] {message}')
        
        emit('sds_alert', {
            'type': alert_type,
            'message': message,
            'severity': severity,  # 'info', 'warning', 'error', 'critical'
            'timestamp': datetime.now().isoformat()
        }, broadcast=True, namespace='/')

from flask_socketio import join_room, leave_room
