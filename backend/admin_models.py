"""
管理员后台系统 - 数据模型
任务: P049-T8-2 管理员后台
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
import json


class AdminUser:
    """管理员用户模型"""
    
    def __init__(self, 
                 id: int = None,
                 username: str = None,
                 email: str = None,
                 password_hash: str = None,
                 role: str = 'operator',
                 status: str = 'active',
                 created_at: str = None,
                 last_login: str = None,
                 permissions: List[str] = None):
        self.id = id
        self.username = username
        self.email = email
        self.password_hash = password_hash
        self.role = role  # super_admin, admin, operator
        self.status = status  # active, disabled
        self.created_at = created_at or datetime.now().isoformat()
        self.last_login = last_login
        self.permissions = permissions or []
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'role': self.role,
            'status': self.status,
            'created_at': self.created_at,
            'last_login': self.last_login,
            'permissions': self.permissions
        }
    
    @classmethod
    def from_db_row(cls, row: tuple) -> 'AdminUser':
        """从数据库行创建对象"""
        if not row:
            return None
        return cls(
            id=row[0],
            username=row[1],
            email=row[2],
            password_hash=row[3],
            role=row[4],
            status=row[5],
            created_at=row[6],
            last_login=row[7],
            permissions=json.loads(row[8]) if row[8] else []
        )


class AdminLog:
    """管理员操作日志模型"""
    
    def __init__(self,
                 id: int = None,
                 admin_id: int = None,
                 admin_username: str = None,
                 action: str = None,
                 target_type: str = None,
                 target_id: str = None,
                 details: Dict[str, Any] = None,
                 ip_address: str = None,
                 created_at: str = None):
        self.id = id
        self.admin_id = admin_id
        self.admin_username = admin_username
        self.action = action
        self.target_type = target_type
        self.target_id = target_id
        self.details = details or {}
        self.ip_address = ip_address
        self.created_at = created_at or datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'admin_id': self.admin_id,
            'admin_username': self.admin_username,
            'action': self.action,
            'target_type': self.target_type,
            'target_id': self.target_id,
            'details': self.details,
            'ip_address': self.ip_address,
            'created_at': self.created_at
        }
    
    @classmethod
    def from_db_row(cls, row: tuple) -> 'AdminLog':
        if not row:
            return None
        return cls(
            id=row[0],
            admin_id=row[1],
            admin_username=row[2],
            action=row[3],
            target_type=row[4],
            target_id=row[5],
            details=json.loads(row[6]) if row[6] else {},
            ip_address=row[7],
            created_at=row[8]
        )


class SystemConfig:
    """系统配置模型"""
    
    def __init__(self,
                 id: int = None,
                 config_key: str = None,
                 config_value: str = None,
                 config_type: str = 'string',
                 description: str = None,
                 updated_at: str = None,
                 updated_by: int = None):
        self.id = id
        self.config_key = config_key
        self.config_value = config_value
        self.config_type = config_type  # string, int, float, bool, json
        self.description = description
        self.updated_at = updated_at or datetime.now().isoformat()
        self.updated_by = updated_by
    
    def get_typed_value(self) -> Any:
        """根据类型返回转换后的值"""
        if self.config_type == 'int':
            return int(self.config_value) if self.config_value else 0
        elif self.config_type == 'float':
            return float(self.config_value) if self.config_value else 0.0
        elif self.config_type == 'bool':
            return self.config_value.lower() in ('true', '1', 'yes', 'on')
        elif self.config_type == 'json':
            return json.loads(self.config_value) if self.config_value else {}
        return self.config_value
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'config_key': self.config_key,
            'config_value': self.config_value,
            'config_type': self.config_type,
            'description': self.description,
            'updated_at': self.updated_at,
            'updated_by': self.updated_by
        }
    
    @classmethod
    def from_db_row(cls, row: tuple) -> 'SystemConfig':
        if not row:
            return None
        return cls(
            id=row[0],
            config_key=row[1],
            config_value=row[2],
            config_type=row[3],
            description=row[4],
            updated_at=row[5],
            updated_by=row[6]
        )


class EmailTemplate:
    """邮件模板模型"""
    
    def __init__(self,
                 id: int = None,
                 template_name: str = None,
                 subject: str = None,
                 body: str = None,
                 variables: List[str] = None,
                 is_active: bool = True,
                 updated_at: str = None,
                 updated_by: int = None):
        self.id = id
        self.template_name = template_name
        self.subject = subject
        self.body = body
        self.variables = variables or []
        self.is_active = is_active
        self.updated_at = updated_at or datetime.now().isoformat()
        self.updated_by = updated_by
    
    def render(self, variables: Dict[str, str]) -> Dict[str, str]:
        """渲染模板"""
        subject = self.subject
        body = self.body
        
        for key, value in variables.items():
            placeholder = f'{{{key}}}'
            subject = subject.replace(placeholder, str(value))
            body = body.replace(placeholder, str(value))
        
        return {'subject': subject, 'body': body}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'template_name': self.template_name,
            'subject': self.subject,
            'body': self.body,
            'variables': self.variables,
            'is_active': self.is_active,
            'updated_at': self.updated_at,
            'updated_by': self.updated_by
        }
    
    @classmethod
    def from_db_row(cls, row: tuple) -> 'EmailTemplate':
        if not row:
            return None
        return cls(
            id=row[0],
            template_name=row[1],
            subject=row[2],
            body=row[3],
            variables=json.loads(row[4]) if row[4] else [],
            is_active=bool(row[5]),
            updated_at=row[6],
            updated_by=row[7]
        )


class TaskQueueItem:
    """任务队列项模型"""
    
    def __init__(self,
                 id: int = None,
                 task_id: str = None,
                 task_type: str = None,
                 status: str = 'pending',
                 priority: int = 0,
                 data: Dict[str, Any] = None,
                 created_at: str = None,
                 started_at: str = None,
                 completed_at: str = None,
                 worker_id: str = None,
                 error_message: str = None):
        self.id = id
        self.task_id = task_id
        self.task_type = task_type
        self.status = status  # pending, running, completed, failed
        self.priority = priority
        self.data = data or {}
        self.created_at = created_at or datetime.now().isoformat()
        self.started_at = started_at
        self.completed_at = completed_at
        self.worker_id = worker_id
        self.error_message = error_message
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'task_id': self.task_id,
            'task_type': self.task_type,
            'status': self.status,
            'priority': self.priority,
            'data': self.data,
            'created_at': self.created_at,
            'started_at': self.started_at,
            'completed_at': self.completed_at,
            'worker_id': self.worker_id,
            'error_message': self.error_message
        }


class WorkerStatus:
    """Worker状态模型"""
    
    def __init__(self,
                 worker_id: str = None,
                 status: str = 'idle',
                 current_task: str = None,
                 last_heartbeat: str = None,
                 cpu_usage: float = 0.0,
                 memory_usage: float = 0.0,
                 tasks_processed: int = 0,
                 tasks_failed: int = 0):
        self.worker_id = worker_id
        self.status = status  # idle, busy, offline
        self.current_task = current_task
        self.last_heartbeat = last_heartbeat or datetime.now().isoformat()
        self.cpu_usage = cpu_usage
        self.memory_usage = memory_usage
        self.tasks_processed = tasks_processed
        self.tasks_failed = tasks_failed
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'worker_id': self.worker_id,
            'status': self.status,
            'current_task': self.current_task,
            'last_heartbeat': self.last_heartbeat,
            'cpu_usage': self.cpu_usage,
            'memory_usage': self.memory_usage,
            'tasks_processed': self.tasks_processed,
            'tasks_failed': self.tasks_failed
        }


class SystemStats:
    """系统统计模型"""
    
    def __init__(self,
                 total_users: int = 0,
                 active_users: int = 0,
                 total_tasks: int = 0,
                 pending_tasks: int = 0,
                 completed_tasks: int = 0,
                 failed_tasks: int = 0,
                 cpu_usage: float = 0.0,
                 memory_usage: float = 0.0,
                 disk_usage: float = 0.0,
                 timestamp: str = None):
        self.total_users = total_users
        self.active_users = active_users
        self.total_tasks = total_tasks
        self.pending_tasks = pending_tasks
        self.completed_tasks = completed_tasks
        self.failed_tasks = failed_tasks
        self.cpu_usage = cpu_usage
        self.memory_usage = memory_usage
        self.disk_usage = disk_usage
        self.timestamp = timestamp or datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'total_users': self.total_users,
            'active_users': self.active_users,
            'total_tasks': self.total_tasks,
            'pending_tasks': self.pending_tasks,
            'completed_tasks': self.completed_tasks,
            'failed_tasks': self.failed_tasks,
            'cpu_usage': self.cpu_usage,
            'memory_usage': self.memory_usage,
            'disk_usage': self.disk_usage,
            'timestamp': self.timestamp
        }
