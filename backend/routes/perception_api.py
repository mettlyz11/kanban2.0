"""Routes: perception_api - PerceptionAgent"""
from flask import Blueprint, jsonify, request
from routes.helpers import get_db, row_to_dict
import os, json, hashlib, threading
from datetime import datetime

bp = Blueprint("routes_perception_api", __name__)
logger = __import__("logging").getLogger(__name__)

class PerceptionRecorder:
    """感知事件记录器 - 直接写入数据库"""

    def record_event(self, event_type, severity, source, message, metadata=None):
        """记录感知事件"""
        try:
            with get_db_connection() as conn:
                c = conn.cursor()
        
                import hashlib
                hash_str = hashlib.md5(f"{event_type}{source}{message}{datetime.now()}".encode()).hexdigest()[:16]
        
                c.execute('''
                    INSERT INTO perception_events 
                    (event_type, severity, source, message, metadata, timestamp, hash)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                ''', (
                    event_type, severity, source, message,
                    json.dumps(metadata) if metadata else '{}',
                    datetime.now().isoformat(), hash_str
                ))
        
                conn.commit()
        except Exception as e:
            logger.error(f"记录感知事件失败: {e}")

    def record_api_error(self, status_code, endpoint, error_message, request_data=None):
        """记录API错误"""
        self.record_event(
            event_type='api_error',
            severity='error' if status_code >= 500 else 'warning',
            source='backend',
            message=f'API错误 {status_code}: {endpoint}',
            metadata={'status_code': status_code, 'endpoint': endpoint, 
                     'error': error_message, 'request': request_data}
        )

# 全局感知记录器实例
perception_recorder = PerceptionRecorder()
_perception_agent = None
def init_perception_agent():
    """初始化感知Agent"""
    global _perception_agent
    if not PERCEPTION_AGENT_AVAILABLE:
        return None

    try:
        config_path = os.path.join(os.path.dirname(__file__), 'perception_config.yml')
        _perception_agent = start_agent(config_path)
        logger.info("✅ PerceptionAgent started successfully")
        return _perception_agent
    except Exception as e:
        logger.error(f"Failed to start PerceptionAgent: {e}")
        return None

def get_perception_agent():
    """获取感知Agent实例"""
    return _perception_agent

# API响应时间监控中间件
@bp.route('/api/perception/status', methods=['GET'])
def perception_status():
    """获取感知Agent状态"""
    if not PERCEPTION_AGENT_AVAILABLE:
        return jsonify({
            'success': False,
            'error': 'PerceptionAgent not available',
            'available': False
        }), 503

    agent = get_perception_agent()
    if not agent:
        return jsonify({
            'success': False,
            'error': 'PerceptionAgent not initialized',
            'available': True,
            'running': False
        })

    status = agent.get_status()
    # Convert listeners object to array for frontend compatibility
    if 'listeners' in status and isinstance(status['listeners'], dict):
        listeners_list = []
        for name, listener_info in status['listeners'].items():
            listener_info_copy = listener_info.copy()
            listener_info_copy['name'] = name
            listeners_list.append(listener_info_copy)
        status['listeners'] = listeners_list
    
    # Convert rules object to array for frontend compatibility
    if 'rules' in status and isinstance(status['rules'], dict):
        rules_list = []
        for name, value in status['rules'].items():
            rules_list.append({'name': name, 'value': value})
        status['rules'] = rules_list
    
    return jsonify({
        'success': True,
        'available': True,
        'status': status
    })

@bp.route('/api/perception/events', methods=['GET'])
def perception_events():
    """获取感知Agent事件日志（从数据库读取）"""
    try:
        limit = request.args.get('limit', 100, type=int)
        event_type = request.args.get('type', None)

        with get_db_connection() as conn:
            c = conn.cursor()

            if event_type:
                c.execute('''
                    SELECT id, event_type, severity, source, message, metadata, timestamp, hash
                    FROM perception_events
                    WHERE event_type = %s
                    ORDER BY timestamp DESC
                    LIMIT %s
                ''', (event_type, limit))
            else:
                c.execute('''
                    SELECT id, event_type, severity, source, message, metadata, timestamp, hash
                    FROM perception_events
                    ORDER BY timestamp DESC
                    LIMIT %s
                ''', (limit,))

            rows = c.fetchall()
            events = []
            for row in rows:
                events.append({
                    'id': str(row['id']),
                    'type': row['event_type'],
                    'severity': row['severity'],
                    'source': row['source'],
                    'message': row['message'],
                    'metadata': json.loads(row['metadata']) if row['metadata'] else {},
                    'timestamp': str(row['timestamp']),
                    'hash': row['hash']
                })

            return jsonify({
                'success': True,
                'events': events,
                'count': len(events)
            })
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        logger.error(f"获取感知事件失败: {type(e).__name__}: {e}")
        logger.error(f"Traceback: {tb}")
        return jsonify({'success': False, 'error': f'{type(e).__name__}: {e}'})

@bp.route('/api/perception/test', methods=['POST'])
def perception_test():
    """测试感知Agent（生成测试事件并保存到数据库）"""
    data = request.get_json() or {}
    event_type = data.get('type', 'test')

    try:
        # 直接保存到数据库
        conn = get_db()
        c = conn.cursor()
    
        timestamp = datetime.now().isoformat()
        import hashlib
        event_hash = hashlib.md5(f"{event_type}{timestamp}".encode()).hexdigest()[:12]
    
        message = data.get('message', f'Test event: {event_type}')
        severity = data.get('severity', 'info')
        source = data.get('source', 'test')
        metadata = json.dumps(data.get('metadata', {}))
    
        c.execute('''
            INSERT INTO perception_events (event_type, severity, source, message, metadata, timestamp, hash)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', (event_type, severity, source, message, metadata, timestamp, event_hash))
    
        conn.commit()

        return jsonify({
            'success': True,
            'message': f'Test event ({event_type}) saved to database',
            'event_id': c.lastrowid
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/perception/record-action', methods=['POST'])
def record_user_action():
    """记录用户行为"""
    if not PERCEPTION_AGENT_AVAILABLE:
        return jsonify({'success': False, 'error': 'PerceptionAgent not available'}), 503

    agent = get_perception_agent()
    if not agent:
        return jsonify({'success': False, 'error': 'PerceptionAgent not initialized'}), 503

    data = request.get_json() or {}
    user_id = data.get('user_id', 'anonymous')
    action = data.get('action')
    target = data.get('target')

    if not action:
        return jsonify({'success': False, 'error': 'Action is required'}), 400

    try:
        agent.record_action(user_id, action, target, data.get('metadata', {}))
        return jsonify({'success': True, 'message': 'Action recorded'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


class PerceptionAgent:
    """
    感知监控系统
    监控系统状态、用户行为、异常事件
    """

    def __init__(self, check_interval=30):
        self.check_interval = check_interval
        self.running = False
        self.thread = None
        self.events = deque(maxlen=1000)  # 保留最近1000个事件
        self.status = {
            'running': False,
            'start_time': None,
            'last_check': None,
            'events_count': 0
        }
        self.monitoring_rules = {
            'cpu_threshold': 80,
            'memory_threshold': 80,
            'disk_threshold': 90
        }

    def start(self):
        """启动感知Agent"""
        if not self.running:
            self.running = True
            self.status['running'] = True
            self.status['start_time'] = datetime.now().isoformat()
            self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.thread.start()
            logger.info("✅ PerceptionAgent 已启动")
            return True
        return False

    def stop(self):
        """停止感知Agent"""
        self.running = False
        self.status['running'] = False
        if self.thread:
            self.thread.join(timeout=5)
        logger.info("🛑 PerceptionAgent 已停止")
        return True

    def _monitor_loop(self):
        """监控循环"""
        while self.running:
            try:
                self._check_system_status()
                self._check_services()
                self.status['last_check'] = datetime.now().isoformat()
                time.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"PerceptionAgent监控错误: {e}")
                time.sleep(5)

    def _check_system_status(self):
        """检查系统状态"""
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory().percent
            disk = psutil.disk_usage('/').percent
        
            if cpu > self.monitoring_rules['cpu_threshold']:
                self.add_event('system', f'CPU使用率过高: {cpu}%', 
                             severity='warning', source='system_monitor')
            if memory > self.monitoring_rules['memory_threshold']:
                self.add_event('system', f'内存使用率过高: {memory}%', 
                             severity='warning', source='system_monitor')
            if disk > self.monitoring_rules['disk_threshold']:
                self.add_event('system', f'磁盘使用率过高: {disk}%', 
                             severity='warning', source='system_monitor')
            
        except ImportError:
            pass  # psutil未安装

    def _check_services(self):
        """检查服务状态"""
        services = [
            {'name': 'kanban', 'url': 'http://localhost:8086/health'},
        ]
    
        for service in services:
            try:
                import urllib.request
                req = urllib.request.Request(service['url'], method='HEAD')
                req.add_header('User-Agent', 'PerceptionAgent/1.0')
                with urllib.request.urlopen(req, timeout=5) as resp:
                    if resp.status != 200:
                        self.add_event('error', f"服务异常: {service['name']} - HTTP {resp.status}", 
                                     severity='error', source='service_check')
            except Exception as e:
                self.add_event('error', f"服务无法访问: {service['name']} - {str(e)}", 
                             severity='error', source='service_check')

    def add_event(self, event_type, message, metadata=None, severity='info', source='system'):
        """添加事件 - 持久化到数据库"""
        try:
            conn = get_db()
            c = conn.cursor()
        
            timestamp = datetime.now().isoformat()
            import hashlib
            event_hash = hashlib.md5(f"{event_type}{message}{timestamp}".encode()).hexdigest()[:12]
        
            metadata_json = json.dumps(metadata) if metadata else '{}'
        
            c.execute('''
                INSERT INTO perception_events (event_type, severity, source, message, metadata, timestamp, hash)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            ''', (event_type, severity, source, message, metadata_json, timestamp, event_hash))
        
            conn.commit()
            event_id = c.lastrowid
        
            # 同时保留内存中的事件（用于快速访问）
            event = {
                'id': event_id,
                'type': event_type,
                'severity': severity,
                'source': source,
                'message': message,
                'timestamp': timestamp,
                'hash': event_hash,
                'metadata': metadata or {}
            }
            self.events.append(event)
            self.status['events_count'] = self._get_db_event_count()
        
            logger.info(f"📡 感知事件已记录: [{event_type}] {message}")
            return event
        
        except Exception as e:
            logger.error(f"保存事件到数据库失败: {e}")
            # 降级到内存存储
            event = {
                'id': len(self.events) + 1,
                'type': event_type,
                'severity': severity,
                'source': source,
                'message': message,
                'timestamp': datetime.now().isoformat(),
                'metadata': metadata or {}
            }
            self.events.append(event)
            self.status['events_count'] = len(self.events)
            return event

    def _get_db_event_count(self):
        """获取数据库中的事件总数"""
        try:
            conn = get_db()
            c = conn.cursor()
            c.execute('SELECT COUNT(*) FROM perception_events')
            return list(c.fetchone().values())[0]
        except:
            return len(self.events)

    def get_events(self, limit=50, event_type=None):
        """获取事件列表 - 从数据库读取"""
        try:
            conn = get_db()
            c = conn.cursor()
        
            if event_type:
                c.execute('''
                    SELECT id, event_type, severity, source, message, metadata, timestamp, hash
                    FROM perception_events
                    WHERE event_type = %s
                    ORDER BY timestamp DESC
                    LIMIT %s
                ''', (event_type, limit))
            else:
                c.execute('''
                    SELECT id, event_type, severity, source, message, metadata, timestamp, hash
                    FROM perception_events
                    ORDER BY timestamp DESC
                    LIMIT %s
                ''', (limit,))
        
            rows = c.fetchall()
            events = []
            for row in rows:
                events.append({
                    'id': str(row['id']),
                    'type': row['event_type'],
                    'severity': row['severity'],
                    'source': row['source'],
                    'message': row['message'],
                    'metadata': json.loads(row['metadata']) if row['metadata'] else {},
                    'timestamp': str(row['timestamp']),
                    'hash': row['hash']
                })
            return events
        
        except Exception as e:
            logger.error(f"从数据库读取事件失败: {e}")
            # 降级到内存存储
            events_list = list(self.events)
            if event_type:
                events_list = [e for e in events_list if e['type'] == event_type]
            return events_list[-limit:]

    def get_status(self):
        """获取状态"""
        # 计算运行时间
        uptime_seconds = 0
        if self.status['start_time']:
            try:
                start = datetime.fromisoformat(self.status['start_time'])
                uptime_seconds = int((datetime.now() - start).total_seconds())
            except:
                pass
    
        return {
            'running': self.running,
            'uptime_seconds': uptime_seconds,
            'event_count': len(self.events),
            'listeners': {
                'log': {'enabled': True, 'running': self.running},
                'error': {'enabled': True, 'running': self.running},
                'metric': {'enabled': True, 'running': self.running},
                'behavior': {'enabled': True, 'running': self.running}
            },
            'start_time': self.status['start_time'],
            'last_check': self.status['last_check'],
            'rules': self.monitoring_rules
        }

    def record_action(self, user_id, action, target, metadata=None):
        """记录用户行为"""
        return self.add_event('action', f"用户 {user_id}: {action}", {
            'user_id': user_id,
            'action': action,
            'target': target,
            'metadata': metadata
        })

    def record_api_error(self, status_code, endpoint, error_message=None, request_data=None):
        """记录API错误"""
        severity = 'critical' if status_code >= 500 else 'high'
        return self.add_event('api_error', f"API错误 {status_code}: {endpoint} - {error_message or 'Unknown'}", {
            'status_code': status_code,
            'endpoint': endpoint,
            'error_message': error_message,
            'request_data': request_data,
            'severity': severity
        })

    def update_config(self, config):
        """更新配置"""
        if 'cpu_threshold' in config:
            self.monitoring_rules['cpu_threshold'] = config['cpu_threshold']
        if 'memory_threshold' in config:
            self.monitoring_rules['memory_threshold'] = config['memory_threshold']
        if 'disk_threshold' in config:
            self.monitoring_rules['disk_threshold'] = config['disk_threshold']
        if 'check_interval' in config:
            self.check_interval = config['check_interval']
        return True

# 全局感知Agent实例
# [DUPLICATE REMOVED] perception_agent = None
# [DUPLICATE REMOVED] PERCEPTION_AGENT_AVAILABLE = False
# [DUPLICATE REMOVED] 
# [DUPLICATE REMOVED] def init_perception_agent():
# [DUPLICATE REMOVED]     """初始化感知Agent"""
# [DUPLICATE REMOVED]     global perception_agent, PERCEPTION_AGENT_AVAILABLE
# [DUPLICATE REMOVED]     try:
# [DUPLICATE REMOVED]         perception_agent = PerceptionAgent()
# [DUPLICATE REMOVED]         perception_agent.start()
# [DUPLICATE REMOVED]         PERCEPTION_AGENT_AVAILABLE = True
# [DUPLICATE REMOVED]         logger.info("✅ 感知Agent初始化成功")
# [DUPLICATE REMOVED]         return True
# [DUPLICATE REMOVED]     except Exception as e:
# [DUPLICATE REMOVED]         logger.error(f"❌ 感知Agent初始化失败: {e}")
# [DUPLICATE REMOVED]         PERCEPTION_AGENT_AVAILABLE = False
# [DUPLICATE REMOVED]         return False
# [DUPLICATE REMOVED] 
# [DUPLICATE REMOVED] def stop_perception_agent():
# [DUPLICATE REMOVED]     """停止感知Agent"""
# [DUPLICATE REMOVED]     global perception_agent, PERCEPTION_AGENT_AVAILABLE
# [DUPLICATE REMOVED]     if perception_agent:
# [DUPLICATE REMOVED]         perception_agent.stop()
# [DUPLICATE REMOVED]         PERCEPTION_AGENT_AVAILABLE = False
# [DUPLICATE REMOVED]         logger.info("🛑 感知Agent已停止")
# [DUPLICATE REMOVED] 
# [DUPLICATE REMOVED] def get_perception_agent():
# [DUPLICATE REMOVED]     """获取感知Agent实例"""
# [DUPLICATE REMOVED]     global perception_agent
# [DUPLICATE REMOVED]     return perception_agent

@bp.route('/api/perception/status', methods=['GET'])
@bp.route('/api/perception/events', methods=['GET'])
def get_perception_events():
    """获取感知事件"""
    global perception_agent, PERCEPTION_AGENT_AVAILABLE
    if perception_agent and PERCEPTION_AGENT_AVAILABLE:
        limit = request.args.get('limit', 50, type=int)
        event_type = request.args.get('type')
        events = perception_agent.get_events(limit=limit, event_type=event_type)
        return jsonify({
            'success': True,
            'available': True,
            'events': events,
            'count': len(events)
        })
    return jsonify({
        'success': True,
        'available': False,
        'events': [],
        'message': 'PerceptionAgent not available'
    })

@bp.route('/api/perception/config', methods=['GET', 'POST'])
def perception_config():
    """获取/更新感知配置"""
    global perception_agent, PERCEPTION_AGENT_AVAILABLE
    if request.method == 'GET':
        if perception_agent and PERCEPTION_AGENT_AVAILABLE:
            # Convert monitoring_rules dict to array for frontend
            rules_list = []
            for key, value in perception_agent.monitoring_rules.items():
                rules_list.append({'name': key, 'value': value})
            
            return jsonify({
                'success': True,
                'available': True,
                'config': rules_list,
                'check_interval': perception_agent.check_interval
            })
        return jsonify({
            'success': True,
            'available': False,
            'config': {}
        })
    else:  # POST
        if perception_agent and PERCEPTION_AGENT_AVAILABLE:
            data = request.get_json() or {}
            perception_agent.update_config(data)
            return jsonify({
                'success': True,
                'message': '配置已更新',
                'config': perception_agent.monitoring_rules
            })
        return jsonify({
            'success': False,
            'error': 'PerceptionAgent not available'
        }), 503

@bp.route('/api/perception/start', methods=['POST'])
def start_perception():
    """启动感知Agent"""
    global PERCEPTION_AGENT_AVAILABLE
    if init_perception_agent():
        return jsonify({
            'success': True,
            'message': 'PerceptionAgent 已启动',
            'available': True
        })
    return jsonify({
        'success': False,
        'error': '启动失败'
    }), 500

@bp.route('/api/perception/stop', methods=['POST'])
def stop_perception():
    """停止感知Agent"""
    global PERCEPTION_AGENT_AVAILABLE
    stop_perception_agent()
    return jsonify({
        'success': True,
        'message': 'PerceptionAgent 已停止',
        'available': False
    })


