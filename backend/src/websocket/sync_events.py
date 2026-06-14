"""
Mac mini 同步数据事件处理
处理来自统一同步服务的 WebSocket 推送
"""
import logging
from datetime import datetime
from flask_socketio import emit

logger = logging.getLogger(__name__)

# 内存存储最新同步数据
_sync_cache = {}

class SyncEventHandler:
    @staticmethod
    def register_events(socketio):
        @socketio.on('macmini_sync')
        def handle_macmini_sync(data):
            sync_type = data.get('type')
            payload = data.get('data', {})
            timestamp = data.get('timestamp', datetime.now().isoformat())
            
            _sync_cache[sync_type] = {
                'data': payload,
                'timestamp': timestamp,
                'updated_at': datetime.now().isoformat()
            }
            
            logger.info(f"📡 收到Mac mini同步: {sync_type}")
            
            # 广播给前端
            event_map = {
                'cron_sync': 'cron_updated',
                'heartbeat_sync': 'heartbeat_updated', 
                'model_config_sync': 'model_config_updated',
                'skills_tools_sync': 'skills_tools_updated',
            }
            
            event_name = event_map.get(sync_type, 'sync_data_updated')
            emit(event_name, {
                'type': sync_type,
                'data': payload,
                'timestamp': timestamp
            }, broadcast=True)
    
    @staticmethod
    def get_cached_data(sync_type):
        return _sync_cache.get(sync_type)
    
    @staticmethod
    def get_all_status():
        return {
            'services': {
                k: v is not None for k, v in _sync_cache.items()
            },
            'last_update': max(
                [v['updated_at'] for v in _sync_cache.values()],
                default=None
            )
        } if _sync_cache else {'services': {}, 'last_update': None}
