"""
System Monitor Real-time Events Module
Handles system alerts, health checks, and resource monitoring
"""
from flask_socketio import emit
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class SystemEventHandler:
    """System Monitor Event Handler"""
    
    _socketio_instance = None
    
    @classmethod
    def set_socketio(cls, sio):
        cls._socketio_instance = sio
    
    @staticmethod
    def register_events(socketio):
        """Register system monitoring events"""
        SystemEventHandler._socketio_instance = socketio
        
        @socketio.on('monitor_subscribe')
        def handle_monitor_subscribe(data):
            """Subscribe to system monitoring"""
            user_id = data.get('user_id')
            if user_id:
                room = f'monitor:{user_id}'
                join_room(room)
                emit('monitor_subscribed', {'status': 'success'})
        
        @socketio.on('monitor_unsubscribe')
        def handle_monitor_unsubscribe(data):
            """Unsubscribe from monitoring"""
            user_id = data.get('user_id')
            if user_id:
                room = f'monitor:{user_id}'
                leave_room(room)
    
    @classmethod
    def emit_system_alert(cls, alert):
        """Emit system alert to all admins"""
        logger.warning(f'System alert: {alert.get("message")}')
        
        sio = cls._socketio_instance
        if not sio:
            return
        sio.emit('system_alert', {
            'id': alert.get('id'),
            'type': alert.get('type'),  # 'cpu', 'memory', 'disk', 'network', 'service'
            'severity': alert.get('severity'),  # 'info', 'warning', 'critical'
            'message': alert.get('message'),
            'metric': alert.get('metric'),
            'threshold': alert.get('threshold'),
            'current_value': alert.get('current_value'),
            'timestamp': datetime.now().isoformat()
        }, broadcast=True, namespace='/')
    
    @classmethod
    def emit_health_status(cls, service_name, status, details=None):
        """Emit service health status"""
        sio = cls._socketio_instance
        if not sio:
            return
        sio.emit('health_status_changed', {
            'service': service_name,
            'status': status,  # 'healthy', 'degraded', 'down'
            'details': details or {},
            'timestamp': datetime.now().isoformat()
        }, broadcast=True, namespace='/')
    
    @classmethod
    def emit_resource_usage(cls, metrics):
        """Emit resource usage metrics"""
        sio = cls._socketio_instance
        if not sio:
            return
        sio.emit('resource_metrics', {
            'cpu': metrics.get('cpu'),
            'memory': metrics.get('memory'),
            'disk': metrics.get('disk'),
            'network': metrics.get('network'),
            'processes': metrics.get('processes'),
            'uptime': metrics.get('uptime'),
            'timestamp': datetime.now().isoformat()
        }, broadcast=True, namespace='/')
    
    @classmethod
    def emit_deployment_status(cls, deployment_info):
        """Emit deployment status"""
        sio = cls._socketio_instance
        if not sio:
            return
        sio.emit('deployment_status', {
            'version': deployment_info.get('version'),
            'status': deployment_info.get('status'),  # 'deploying', 'completed', 'failed'
            'progress': deployment_info.get('progress', 0),
            'message': deployment_info.get('message'),
            'timestamp': datetime.now().isoformat()
        }, broadcast=True, namespace='/')

from flask_socketio import join_room, leave_room
