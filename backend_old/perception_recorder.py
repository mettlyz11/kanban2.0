import sqlite3
import json
from datetime import datetime

class PerceptionRecorder:
    """感知事件记录器 - 直接写入数据库"""
    
    def __init__(self, db_path='/opt/kanban-react/backend/kanban_v5.db'):
        self.db_path = db_path
    
    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def record_event(self, event_type, severity, source, message, metadata=None):
        """记录感知事件"""
        try:
            conn = self._get_conn()
            c = conn.cursor()
            
            # 生成简单hash
            import hashlib
            hash_str = hashlib.md5(f"{event_type}{source}{message}{datetime.now()}".encode()).hexdigest()[:16]
            
            c.execute('''
                INSERT INTO perception_events 
                (event_type, severity, source, message, metadata, timestamp, hash)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                event_type,
                severity,
                source,
                message,
                json.dumps(metadata) if metadata else '{}',
                datetime.now().isoformat(),
                hash_str
            ))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"记录感知事件失败: {e}")
            return False
    
    def record_api_error(self, status_code, endpoint, error_message, request_data=None):
        """记录API错误"""
        return self.record_event(
            event_type='api_error',
            severity='error' if status_code >= 500 else 'warning',
            source='backend',
            message=f'API错误 {status_code}: {endpoint} - {error_message}',
            metadata={
                'status_code': status_code,
                'endpoint': endpoint,
                'request_data': request_data or {}
            }
        )
    
    def record_system_event(self, event_name, details=None):
        """记录系统事件"""
        return self.record_event(
            event_type='system_event',
            severity='info',
            source='system',
            message=event_name,
            metadata=details or {}
        )
    
    def record_user_action(self, action, user=None, details=None):
        """记录用户操作"""
        return self.record_event(
            event_type='user_action',
            severity='info',
            source='frontend',
            message=f'用户操作: {action}',
            metadata={
                'user': user,
                'action': action,
                'details': details or {}
            }
        )
    
    def record_security_event(self, event_type, details):
        """记录安全事件"""
        return self.record_event(
            event_type='security_alert',
            severity='warning',
            source='security',
            message=f'安全事件: {event_type}',
            metadata=details
        )

# 测试记录一些事件
if __name__ == '__main__':
    recorder = PerceptionRecorder()
    
    print("记录测试事件...")
    
    # 记录API错误
    recorder.record_api_error(
        status_code=500,
        endpoint='/api/test',
        error_message='数据库连接超时',
        request_data={'method': 'GET'}
    )
    
    # 记录系统事件
    recorder.record_system_event(
        '系统启动',
        {'version': 'v2.4.11', 'server': 'aliyun'}
    )
    
    # 记录用户操作
    recorder.record_user_action(
        '查看感知监控',
        user='admin',
        details={'page': 'perception-monitor'}
    )
    
    # 记录安全事件
    recorder.record_security_event(
        '异常登录尝试',
        {'ip': '192.168.1.100', 'attempts': 3}
    )
    
    print("✅ 测试事件记录完成")
    
    # 验证
    conn = sqlite3.connect('/opt/kanban-react/backend/kanban_v5.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM perception_events")
    count = c.fetchone()[0]
    print(f"当前事件总数: {count}")
    conn.close()
