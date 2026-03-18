from flask import Blueprint, request, jsonify
from database_config import get_db_connection
import os
import json
from datetime import datetime
from pathlib import Path

# 创建蓝图
perception_bp = Blueprint('perception', __name__, url_prefix='/api/perception')

# 数据库路径
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'kanban_v5.db')

# 感知 Agent 实例
_agent = None

def get_agent():
    """获取感知 Agent 实例"""
    global _agent
    if _agent is None:
        try:
            from perception_agent import get_agent as get_perception_agent
            _agent = get_perception_agent()
        except Exception as e:
            print(f"获取感知 Agent 失败：{e}")
    return _agent

def init_agent():
    """初始化感知 Agent"""
    global _agent
    if _agent is None:
        try:
            from perception_agent import init_agent as init_perception_agent
            config_path = os.path.join(os.path.dirname(__file__), 'perception_config.yml')
            _agent = init_perception_agent(config_path)
        except Exception as e:
            print(f"初始化感知 Agent 失败：{e}")
    return _agent


@perception_bp.route('/status', methods=['GET'])
def get_status():
    """获取感知 Agent 状态"""
    try:
        agent = get_agent()
        if agent:
            status = agent.get_status()
            return jsonify({
                'success': True,
                'data': status
            })
        else:
            return jsonify({
                'success': True,
                'data': {
                    'running': False,
                    'message': '感知 Agent 未启动'
                }
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@perception_bp.route('/events', methods=['GET'])
def get_events():
    """获取感知事件日志"""
    try:
        # 获取查询参数
        limit = request.args.get('limit', 100, type=int)
        severity = request.args.get('severity', None)
        event_type = request.args.get('type', None)
        offset = request.args.get('offset', 0, type=int)
        
        with get_db_connection() as conn:
        
        cursor = conn.cursor()
        
        # 构建查询
        query = 'SELECT * FROM perception_events WHERE 1=1'
        params = []
        
        if severity:
            query += ' AND severity = ?'
            params.append(severity)
        
        if event_type:
            query += ' AND event_type = ?'
            params.append(event_type)
        
        query += ' ORDER BY timestamp DESC LIMIT ? OFFSET ?'
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        # 获取总数
        count_query = 'SELECT COUNT(*) FROM perception_events WHERE 1=1'
        count_params = []
        
        if severity:
            count_query += ' AND severity = ?'
            count_params.append(severity)
        
        if event_type:
            count_query += ' AND event_type = ?'
            count_params.append(event_type)
        
        cursor.execute(count_query, count_params)
        total = cursor.fetchone()[0]
        
        conn.close()
        
        # 转换为字典
        events = []
        for row in rows:
            event = {
                'id': row['id'],
                'event_type': row['event_type'],
                'severity': row['severity'],
                'source': row['source'],
                'message': row['message'],
                'metadata': json.loads(row['metadata']) if row['metadata'] else {},
                'timestamp': row['timestamp'],
                'hash': row['hash'],
                'processed': bool(row['processed'])
            }
            events.append(event)
        
        return jsonify({
            'success': True,
            'data': {
                'events': events,
                'total': total,
                'limit': limit,
                'offset': offset
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@perception_bp.route('/test', methods=['POST'])
def test_event():
    """发送测试事件"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': '缺少请求数据'
            }), 400
        
        event_type = data.get('type', 'test')
        severity = data.get('severity', 'low')
        message = data.get('message', '测试事件')
        metadata = data.get('metadata', {})
        
        # 记录到数据库
        with get_db_connection() as conn:
        cursor = conn.cursor()
        
        import hashlib
        hash_str = hashlib.md5(f"{event_type}test{message}{datetime.now()}".encode()).hexdigest()[:16]
        
        cursor.execute('''
            INSERT INTO perception_events 
            (event_type, severity, source, message, metadata, timestamp, hash)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            event_type, severity, 'test_client', message,
            json.dumps(metadata), datetime.now().isoformat(), hash_str
        ))
        
        conn.commit()
        conn.close()
        
        # 如果 Agent 运行中，也触发事件
        agent = get_agent()
        if agent:
            from perception_agent import PerceptionEvent
            event = PerceptionEvent(
                event_type=event_type,
                severity=severity,
                source='test_client',
                message=message,
                data=metadata
            )
            agent._on_event(event)
        
        return jsonify({
            'success': True,
            'message': '测试事件已记录',
            'event': {
                'type': event_type,
                'severity': severity,
                'message': message
            }
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@perception_bp.route('/config', methods=['GET'])
def get_config():
    """获取感知 Agent 配置"""
    try:
        config_path = os.path.join(os.path.dirname(__file__), 'perception_config.yml')
        
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config_content = f.read()
            
            # 尝试解析 YAML
            try:
                import yaml
                config = yaml.safe_load(config_content)
                return jsonify({
                    'success': True,
                    'data': config,
                    'format': 'yaml'
                })
            except ImportError:
                return jsonify({
                    'success': True,
                    'data': {'raw': config_content},
                    'format': 'yaml_raw'
                })
        else:
            return jsonify({
                'success': True,
                'data': {'message': '配置文件不存在，使用默认配置'},
                'format': 'default'
            })
            
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@perception_bp.route('/record-action', methods=['POST'])
def record_action():
    """记录用户行为"""
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                'success': False,
                'error': '缺少请求数据'
            }), 400
        
        user_id = data.get('user_id')
        action = data.get('action')
        target = data.get('target')
        metadata = data.get('metadata', {})
        
        if not user_id or not action:
            return jsonify({
                'success': False,
                'error': '缺少必要参数：user_id, action'
            }), 400
        
        # 记录到数据库
        with get_db_connection() as conn:
        cursor = conn.cursor()
        
        import hashlib
        hash_str = hashlib.md5(f"action{user_id}{action}{datetime.now()}".encode()).hexdigest()[:16]
        
        cursor.execute('''
            INSERT INTO perception_events 
            (event_type, severity, source, message, metadata, timestamp, hash)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            'user_action', 'info', 'user',
            f'用户 {user_id[:8]}... 执行了 {action}',
            json.dumps({'user_id': user_id, 'action': action, 'target': target, **metadata}),
            datetime.now().isoformat(), hash_str
        ))
        
        conn.commit()
        conn.close()
        
        # 如果 Agent 运行中，也触发事件
        agent = get_agent()
        if agent:
            agent.record_action(
                user_id=user_id,
                action=action,
                target=target,
                metadata=metadata
            )
        
        return jsonify({
            'success': True,
            'message': '用户行为已记录'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@perception_bp.route('/start', methods=['POST'])
def start_agent_route():
    """启动感知 Agent"""
    try:
        agent = init_agent()
        if agent:
            agent.start()
            return jsonify({
                'success': True,
                'message': '感知 Agent 已启动',
                'status': agent.get_status()
            })
        else:
            return jsonify({
                'success': False,
                'error': '无法初始化感知 Agent'
            }), 500
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@perception_bp.route('/stop', methods=['POST'])
def stop_agent_route():
    """停止感知 Agent"""
    try:
        agent = get_agent()
        if agent:
            agent.stop()
            return jsonify({
                'success': True,
                'message': '感知 Agent 已停止'
            })
        else:
            return jsonify({
                'success': True,
                'message': '感知 Agent 未运行'
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
