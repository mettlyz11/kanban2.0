"""
同步数据 API 路由
提供 Mac mini 推送数据的查询接口
"""
from flask import Blueprint, jsonify, request
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

sync_bp = Blueprint('sync', __name__)

# 内存存储
_sync_data = {
    'cron': None,
    'heartbeat': None,
    'model_config': None,
    'skills_tools': None,
    'monitor': None
}

@sync_bp.route('/api/sync/status', methods=['GET'])
def get_sync_status():
    """获取同步状态"""
    status = {
        'services': {k: v is not None for k, v in _sync_data.items()},
        'last_updates': {k: v['timestamp'] if v else None for k, v in _sync_data.items()}
    }
    return jsonify({'success': True, 'status': status})

@sync_bp.route('/api/sync/cron', methods=['GET'])
def get_cron_data():
    """获取 Cron 数据"""
    data = _sync_data.get('cron')
    if data:
        return jsonify({'success': True, 'data': data['data'], 'timestamp': data['timestamp']})
    return jsonify({'success': False, 'error': 'No cron data'})

@sync_bp.route('/api/sync/heartbeat', methods=['GET'])
def get_heartbeat_data():
    """获取心跳数据"""
    data = _sync_data.get('heartbeat')
    if data:
        return jsonify({'success': True, 'data': data['data'], 'timestamp': data['timestamp']})
    return jsonify({'success': False, 'error': 'No heartbeat data'})

@sync_bp.route('/api/sync/model-config', methods=['GET'])
def get_model_config_data():
    """获取模型配置"""
    data = _sync_data.get('model_config')
    if data:
        return jsonify({'success': True, 'data': data['data'], 'timestamp': data['timestamp']})
    return jsonify({'success': False, 'error': 'No model config data'})

@sync_bp.route('/api/sync/skills-tools', methods=['GET'])
def get_skills_tools_data():
    """获取 Skills/Tools"""
    data = _sync_data.get('skills_tools')
    if data:
        return jsonify({'success': True, 'data': data['data'], 'timestamp': data['timestamp']})
    return jsonify({'success': False, 'error': 'No skills/tools data'})

@sync_bp.route('/api/sync/monitor', methods=['GET'])
def get_monitor_data():
    """获取监控数据"""
    data = _sync_data.get('monitor')
    if data:
        return jsonify({'success': True, 'data': data['data'], 'timestamp': data['timestamp']})
    return jsonify({'success': False, 'error': 'No monitor data'})

# 推送接口（Mac mini 调用）
@sync_bp.route('/api/sync/push', methods=['POST'])
def push_sync_data():
    """接收 Mac mini 推送的同步数据"""
    data = request.json
    sync_type = data.get('type')
    
    if sync_type in _sync_data:
        _sync_data[sync_type] = {
            'data': data.get('data'),
            'timestamp': data.get('timestamp', datetime.now().isoformat())
        }
        logger.info(f"✅ 同步数据已接收: {sync_type}")
        return jsonify({'success': True})
    
    return jsonify({'success': False, 'error': 'Unknown sync type'})

def get_sync_store():
    return _sync_data
