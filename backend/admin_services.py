"""
管理员后台系统 - 业务逻辑服务
任务: P049-T8-2 管理员后台
"""

import json
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from database_config import get_db_connection, row_to_dict
from admin_models import (
    AdminUser, AdminLog, SystemConfig, EmailTemplate,
    TaskQueueItem, WorkerStatus, SystemStats
)


class AdminService:
    """管理员服务基类"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
    
    def get_db_connection(self):
        """获取数据库连接（MySQL via database_config）"""
        conn = get_db_connection()
        
        return conn


class UserManagementService(AdminService):
    """用户管理服务"""
    
    def get_users(self, 
                  page: int = 1, 
                  per_page: int = 20,
                  status: str = None,
                  role: str = None,
                  search: str = None) -> Dict[str, Any]:
        """获取用户列表"""
        conn = self.get_db_connection()
        c = conn.cursor()
        
        # 构建查询条件
        conditions = []
        params = []
        
        if status:
            conditions.append("status = %s")
            params.append(status)
        if role:
            conditions.append("role = %s")
            params.append(role)
        if search:
            conditions.append("(username LIKE %s OR email LIKE %s)")
            params.extend([f"%{search}%", f"%{search}%"])
        
        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
        
        # 获取总数
        count_sql = f"SELECT COUNT(*) FROM users {where_clause}"
        c.execute(count_sql, params)
        total = c.fetchone()[0]
        
        # 获取分页数据
        offset = (page - 1) * per_page
        sql = f"""
            SELECT id, username, email, role, status, created_at, last_login
            FROM users
            {where_clause}
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
        """
        c.execute(sql, params + [per_page, offset])
        rows = c.fetchall()
        
        users = []
        for row in rows:
            users.append(row_to_dict(row, c))
        
        conn.close()
        
        return {
            'users': users,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page
        }
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict[str, Any]]:
        """获取用户详情"""
        conn = self.get_db_connection()
        c = conn.cursor()
        
        c.execute("""
            SELECT id, username, email, role, status, created_at, last_login
            FROM users WHERE id = %s
        """, (user_id,))
        
        row = c.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return row_to_dict(row, c)
    
    def update_user_status(self, user_id: int, status: str) -> Dict[str, Any]:
        """更新用户状态（禁用/启用）"""
        if status not in ['active', 'disabled']:
            return {'success': False, 'error': '无效的状态值'}
        
        conn = self.get_db_connection()
        c = conn.cursor()
        
        try:
            c.execute(
                "UPDATE users SET status = %s WHERE id = %s",
                (status, user_id)
            )
            conn.commit()
            
            if c.rowcount == 0:
                return {'success': False, 'error': '用户不存在'}
            
            return {'success': True, 'message': f'用户已{"启用" if status == "active" else "禁用"}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
        finally:
            conn.close()
    
    def update_user_role(self, user_id: int, role: str) -> Dict[str, Any]:
        """更新用户角色"""
        valid_roles = ['user', 'admin', 'super_admin']
        if role not in valid_roles:
            return {'success': False, 'error': f'无效的角色，必须是: {", ".join(valid_roles)}'}
        
        conn = self.get_db_connection()
        c = conn.cursor()
        
        try:
            c.execute(
                "UPDATE users SET role = %s WHERE id = %s",
                (role, user_id)
            )
            conn.commit()
            
            if c.rowcount == 0:
                return {'success': False, 'error': '用户不存在'}
            
            return {'success': True, 'message': f'用户角色已更新为 {role}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
        finally:
            conn.close()
    
    def delete_user(self, user_id: int) -> Dict[str, Any]:
        """删除用户"""
        conn = self.get_db_connection()
        c = conn.cursor()
        
        try:
            c.execute("DELETE FROM users WHERE id = %s", (user_id,))
            conn.commit()
            
            if c.rowcount == 0:
                return {'success': False, 'error': '用户不存在'}
            
            return {'success': True, 'message': '用户已删除'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
        finally:
            conn.close()
    
    def get_user_stats(self) -> Dict[str, Any]:
        """获取用户统计"""
        conn = self.get_db_connection()
        c = conn.cursor()
        
        # 总用户数
        c.execute("SELECT COUNT(*) FROM users")
        total = c.fetchone()[0]
        
        # 活跃用户数
        c.execute("SELECT COUNT(*) FROM users WHERE status = 'active'")
        active = c.fetchone()[0]
        
        # 禁用用户数
        c.execute("SELECT COUNT(*) FROM users WHERE status = 'disabled'")
        disabled = c.fetchone()[0]
        
        # 今日新增
        today = datetime.now().strftime('%Y-%m-%d')
        c.execute(
            "SELECT COUNT(*) FROM users WHERE DATE(created_at) = %s",
            (today,)
        )
        new_today = c.fetchone()[0]
        
        # 角色分布
        c.execute("""
            SELECT role, COUNT(*) as count 
            FROM users 
            GROUP BY role
        """)
        role_distribution = {row[0]: row[1] for row in c.fetchall()}
        
        conn.close()
        
        return {
            'total': total,
            'active': active,
            'disabled': disabled,
            'new_today': new_today,
            'role_distribution': role_distribution
        }


class TaskMonitorService(AdminService):
    """任务监控服务"""
    
    def get_task_queue_status(self) -> Dict[str, Any]:
        """获取任务队列状态"""
        conn = self.get_db_connection()
        c = conn.cursor()
        
        # 各状态任务数
        c.execute("""
            SELECT status, COUNT(*) as count 
            FROM tasks 
            GROUP BY status
        """)
        status_counts = {row[0]: row[1] for row in c.fetchall()}
        
        # 最近24小时的任务
        yesterday = (datetime.now() - timedelta(days=1)).isoformat()
        c.execute("""
            SELECT status, COUNT(*) as count 
            FROM tasks 
            WHERE created_at > %s
            GROUP BY status
        """, (yesterday,))
        recent_counts = {row[0]: row[1] for row in c.fetchall()}
        
        # 待处理任务详情
        c.execute("""
            SELECT id, title, status, priority, created_at
            FROM tasks 
            WHERE status IN ('pending', 'queued')
            ORDER BY priority DESC, created_at ASC
            LIMIT 20
        """)
        pending_tasks = []
        for row in c.fetchall():
            pending_tasks.append(row_to_dict(row, c))
        
        conn.close()
        
        return {
            'total_by_status': status_counts,
            'recent_24h': recent_counts,
            'pending_tasks': pending_tasks
        }
    
    def get_worker_status(self) -> List[Dict[str, Any]]:
        """获取Worker状态"""
        # 这里模拟Worker状态，实际应从Worker管理器获取
        workers = [
            {
                'worker_id': 'worker-1',
                'status': 'idle',
                'current_task': None,
                'last_heartbeat': datetime.now().isoformat(),
                'cpu_usage': 15.5,
                'memory_usage': 32.0,
                'tasks_processed': 150,
                'tasks_failed': 2
            },
            {
                'worker_id': 'worker-2',
                'status': 'busy',
                'current_task': 'task-123',
                'last_heartbeat': datetime.now().isoformat(),
                'cpu_usage': 65.2,
                'memory_usage': 48.5,
                'tasks_processed': 230,
                'tasks_failed': 5
            }
        ]
        return workers
    
    def get_resource_usage(self) -> Dict[str, Any]:
        """获取资源使用情况"""
        import psutil
        
        # CPU使用率
        cpu_percent = psutil.cpu_percent(interval=1)
        cpu_count = psutil.cpu_count()
        
        # 内存使用
        memory = psutil.virtual_memory()
        
        # 磁盘使用
        disk = psutil.disk_usage('/')
        
        # 网络IO
        net_io = psutil.net_io_counters()
        
        return {
            'cpu': {
                'percent': cpu_percent,
                'count': cpu_count,
                'per_cpu': psutil.cpu_percent(interval=0.1, percpu=True)
            },
            'memory': {
                'total': memory.total,
                'available': memory.available,
                'percent': memory.percent,
                'used': memory.used,
                'free': memory.free
            },
            'disk': {
                'total': disk.total,
                'used': disk.used,
                'free': disk.free,
                'percent': (disk.used / disk.total) * 100
            },
            'network': {
                'bytes_sent': net_io.bytes_sent,
                'bytes_recv': net_io.bytes_recv,
                'packets_sent': net_io.packets_sent,
                'packets_recv': net_io.packets_recv
            },
            'timestamp': datetime.now().isoformat()
        }


class ConfigService(AdminService):
    """系统配置服务"""
    
    def get_all_configs(self) -> List[Dict[str, Any]]:
        """获取所有配置"""
        conn = self.get_db_connection()
        c = conn.cursor()
        
        c.execute("""
            SELECT id, config_key, config_value, config_type, description, updated_at
            FROM system_config
            ORDER BY config_key
        """)
        
        configs = []
        for row in c.fetchall():
            configs.append(row_to_dict(row, c))
        
        conn.close()
        return configs
    
    def get_config(self, key: str) -> Optional[Dict[str, Any]]:
        """获取单个配置"""
        conn = self.get_db_connection()
        c = conn.cursor()
        
        c.execute(
            "SELECT * FROM system_config WHERE config_key = %s",
            (key,)
        )
        row = c.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return SystemConfig.from_db_row(row).to_dict()
    
    def update_config(self, key: str, value: str, updated_by: int = None) -> Dict[str, Any]:
        """更新配置"""
        conn = self.get_db_connection()
        c = conn.cursor()
        
        try:
            c.execute("""
                UPDATE system_config 
                SET config_value = %s, updated_at = %s, updated_by = %s
                WHERE config_key = %s
            """, (value, datetime.now().isoformat(), updated_by, key))
            
            conn.commit()
            
            if c.rowcount == 0:
                return {'success': False, 'error': '配置项不存在'}
            
            return {'success': True, 'message': '配置已更新'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
        finally:
            conn.close()
    
    def get_email_templates(self) -> List[Dict[str, Any]]:
        """获取邮件模板列表"""
        conn = self.get_db_connection()
        c = conn.cursor()
        
        c.execute("""
            SELECT id, template_name, subject, variables, is_active, updated_at
            FROM email_templates
            ORDER BY template_name
        """)
        
        templates = []
        for row in c.fetchall():
            templates.append(row_to_dict(row, c))
        
        conn.close()
        return templates
    
    def get_email_template(self, template_id: int) -> Optional[Dict[str, Any]]:
        """获取邮件模板详情"""
        conn = self.get_db_connection()
        c = conn.cursor()
        
        c.execute(
            "SELECT * FROM email_templates WHERE id = %s",
            (template_id,)
        )
        row = c.fetchone()
        conn.close()
        
        if not row:
            return None
        
        return EmailTemplate.from_db_row(row).to_dict()
    
    def update_email_template(self, 
                              template_id: int,
                              subject: str,
                              body: str,
                              updated_by: int = None) -> Dict[str, Any]:
        """更新邮件模板"""
        conn = self.get_db_connection()
        c = conn.cursor()
        
        try:
            c.execute("""
                UPDATE email_templates 
                SET subject = %s, body = %s, updated_at = %s, updated_by = %s
                WHERE id = %s
            """, (subject, body, datetime.now().isoformat(), updated_by, template_id))
            
            conn.commit()
            
            if c.rowcount == 0:
                return {'success': False, 'error': '模板不存在'}
            
            return {'success': True, 'message': '模板已更新'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
        finally:
            conn.close()


class LogService(AdminService):
    """日志服务"""
    
    def get_system_logs(self,
                       level: str = None,
                       source: str = None,
                       start_time: str = None,
                       end_time: str = None,
                       page: int = 1,
                       per_page: int = 50) -> Dict[str, Any]:
        """获取系统日志"""
        conn = self.get_db_connection()
        c = conn.cursor()
        
        # 构建查询条件
        conditions = []
        params = []
        
        if level:
            conditions.append("level = %s")
            params.append(level)
        if source:
            conditions.append("source LIKE %s")
            params.append(f"%{source}%")
        if start_time:
            conditions.append("timestamp >= %s")
            params.append(start_time)
        if end_time:
            conditions.append("timestamp <= %s")
            params.append(end_time)
        
        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
        
        # 获取总数
        count_sql = f"SELECT COUNT(*) FROM system_logs {where_clause}"
        c.execute(count_sql, params)
        total = c.fetchone()[0]
        
        # 获取分页数据
        offset = (page - 1) * per_page
        sql = f"""
            SELECT id, level, source, message, timestamp, metadata
            FROM system_logs
            {where_clause}
            ORDER BY timestamp DESC
            LIMIT %s OFFSET %s
        """
        c.execute(sql, params + [per_page, offset])
        
        logs = []
        for row in c.fetchall():
            logs.append(row_to_dict(row, c))
        
        conn.close()
        
        return {
            'logs': logs,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page
        }
    
    def get_audit_logs(self,
                      admin_id: int = None,
                      action: str = None,
                      target_type: str = None,
                      page: int = 1,
                      per_page: int = 50) -> Dict[str, Any]:
        """获取审计日志"""
        conn = self.get_db_connection()
        c = conn.cursor()
        
        # 构建查询条件
        conditions = []
        params = []
        
        if admin_id:
            conditions.append("admin_id = %s")
            params.append(admin_id)
        if action:
            conditions.append("action = %s")
            params.append(action)
        if target_type:
            conditions.append("target_type = %s")
            params.append(target_type)
        
        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
        
        # 获取总数
        count_sql = f"SELECT COUNT(*) FROM admin_logs {where_clause}"
        c.execute(count_sql, params)
        total = c.fetchone()[0]
        
        # 获取分页数据
        offset = (page - 1) * per_page
        sql = f"""
            SELECT id, admin_id, admin_username, action, target_type, target_id,
                   details, ip_address, created_at
            FROM admin_logs
            {where_clause}
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
        """
        c.execute(sql, params + [per_page, offset])
        
        logs = []
        for row in c.fetchall():
            logs.append(row_to_dict(row, c))
        
        conn.close()
        
        return {
            'logs': logs,
            'total': total,
            'page': page,
            'per_page': per_page,
            'total_pages': (total + per_page - 1) // per_page
        }
    
    def log_admin_action(self,
                        admin_id: int,
                        admin_username: str,
                        action: str,
                        target_type: str,
                        target_id: str = None,
                        details: Dict[str, Any] = None,
                        ip_address: str = None):
        """记录管理员操作"""
        conn = self.get_db_connection()
        c = conn.cursor()
        
        try:
            c.execute("""
                INSERT INTO admin_logs 
                (admin_id, admin_username, action, target_type, target_id, details, ip_address, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                admin_id, admin_username, action, target_type, target_id,
                json.dumps(details) if details else '{}',
                ip_address,
                datetime.now().isoformat()
            ))
            conn.commit()
        except Exception as e:
            print(f"记录审计日志失败: {e}")
        finally:
            conn.close()


class DashboardService(AdminService):
    """仪表盘数据服务"""
    
    def get_dashboard_stats(self) -> Dict[str, Any]:
        """获取仪表盘统计数据"""
        conn = self.get_db_connection()
        c = conn.cursor()
        
        # 用户统计
        c.execute("SELECT COUNT(*) FROM users")
        total_users = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM users WHERE status = 'active'")
        active_users = c.fetchone()[0]
        
        # 任务统计
        c.execute("SELECT COUNT(*) FROM tasks")
        total_tasks = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM tasks WHERE status = 'pending'")
        pending_tasks = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM tasks WHERE status = 'completed'")
        completed_tasks = c.fetchone()[0]
        
        # 最近7天任务趋势
        week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        c.execute("""
            SELECT DATE(created_at) as date, COUNT(*) as count
            FROM tasks
            WHERE DATE(created_at) >= %s
            GROUP BY DATE(created_at)
            ORDER BY date
        """, (week_ago,))
        task_trend = {row[0]: row[1] for row in c.fetchall()}
        
        # 项目统计
        c.execute("SELECT COUNT(*) FROM projects")
        total_projects = c.fetchone()[0]
        
        # 最近登录
        c.execute("""
            SELECT username, last_login
            FROM users
            WHERE last_login IS NOT NULL
            ORDER BY last_login DESC
            LIMIT 5
        """)
        recent_logins = [row_to_dict(row, c) for row in c.fetchall()]
        
        conn.close()
        
        return {
            'users': {
                'total': total_users,
                'active': active_users,
                'inactive': total_users - active_users
            },
            'tasks': {
                'total': total_tasks,
                'pending': pending_tasks,
                'completed': completed_tasks,
                'completion_rate': round(completed_tasks / total_tasks * 100, 2) if total_tasks > 0 else 0
            },
            'projects': {
                'total': total_projects
            },
            'task_trend': task_trend,
            'recent_logins': recent_logins
        }
    
    def get_system_health(self) -> Dict[str, Any]:
        """获取系统健康状态"""
        import psutil
        
        # 系统资源
        cpu_percent = psutil.cpu_percent(interval=0.5)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # 数据库状态
        conn = self.get_db_connection()
        c = conn.cursor()
        
        # 检查数据库是否可写
        try:
            c.execute("SELECT 1")
            db_status = 'healthy'
        except:
            db_status = 'error'
        
        conn.close()
        
        # 判断健康状态
        health_status = 'healthy'
        issues = []
        
        if cpu_percent > 90:
            health_status = 'warning'
            issues.append('CPU使用率过高')
        elif cpu_percent > 95:
            health_status = 'critical'
        
        if memory.percent > 90:
            health_status = 'warning'
            issues.append('内存使用率过高')
        elif memory.percent > 95:
            health_status = 'critical'
        
        if disk.percent > 90:
            health_status = 'warning'
            issues.append('磁盘空间不足')
        
        if db_status != 'healthy':
            health_status = 'critical'
            issues.append('数据库异常')
        
        return {
            'status': health_status,
            'issues': issues,
            'cpu': {
                'percent': cpu_percent,
                'status': 'critical' if cpu_percent > 95 else 'warning' if cpu_percent > 80 else 'healthy'
            },
            'memory': {
                'percent': memory.percent,
                'status': 'critical' if memory.percent > 95 else 'warning' if memory.percent > 80 else 'healthy'
            },
            'disk': {
                'percent': disk.percent,
                'status': 'critical' if disk.percent > 95 else 'warning' if disk.percent > 80 else 'healthy'
            },
            'database': {
                'status': db_status
            },
            'timestamp': datetime.now().isoformat()
        }
