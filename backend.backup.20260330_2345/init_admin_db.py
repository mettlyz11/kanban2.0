"""
管理员后台系统 - 数据库初始化
任务: P049-T8-2 管理员后台
"""

import sqlite3
import os
import json


def init_admin_tables(db_path: str):
    """初始化管理员后台相关表"""
    
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # 1. 管理员操作日志表
    c.execute('''
        CREATE TABLE IF NOT EXISTS admin_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_id INTEGER,
            admin_username TEXT,
            action TEXT NOT NULL,
            target_type TEXT,
            target_id TEXT,
            details TEXT DEFAULT '{}',
            ip_address TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (admin_id) REFERENCES users(id)
        )
    ''')
    
    # 创建索引
    c.execute('''
        CREATE INDEX IF NOT EXISTS idx_admin_logs_admin_id 
        ON admin_logs(admin_id)
    ''')
    c.execute('''
        CREATE INDEX IF NOT EXISTS idx_admin_logs_action 
        ON admin_logs(action)
    ''')
    c.execute('''
        CREATE INDEX IF NOT EXISTS idx_admin_logs_created_at 
        ON admin_logs(created_at)
    ''')
    
    # 2. 系统配置表
    c.execute('''
        CREATE TABLE IF NOT EXISTS system_config (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            config_key TEXT UNIQUE NOT NULL,
            config_value TEXT,
            config_type TEXT DEFAULT 'string',
            description TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_by INTEGER,
            FOREIGN KEY (updated_by) REFERENCES users(id)
        )
    ''')
    
    # 3. 邮件模板表
    c.execute('''
        CREATE TABLE IF NOT EXISTS email_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            template_name TEXT UNIQUE NOT NULL,
            subject TEXT NOT NULL,
            body TEXT NOT NULL,
            variables TEXT DEFAULT '[]',
            is_active INTEGER DEFAULT 1,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_by INTEGER,
            FOREIGN KEY (updated_by) REFERENCES users(id)
        )
    ''')
    
    # 4. 系统日志表（如果不存在）
    c.execute('''
        CREATE TABLE IF NOT EXISTS system_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            level TEXT DEFAULT 'INFO',
            source TEXT,
            message TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            metadata TEXT DEFAULT '{}'
        )
    ''')
    
    # 创建索引
    c.execute('''
        CREATE INDEX IF NOT EXISTS idx_system_logs_level 
        ON system_logs(level)
    ''')
    c.execute('''
        CREATE INDEX IF NOT EXISTS idx_system_logs_timestamp 
        ON system_logs(timestamp)
    ''')
    
    # 5. 任务队列表（如果不存在）
    c.execute('''
        CREATE TABLE IF NOT EXISTS task_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT UNIQUE NOT NULL,
            task_type TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            priority INTEGER DEFAULT 0,
            data TEXT DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            started_at TIMESTAMP,
            completed_at TIMESTAMP,
            worker_id TEXT,
            error_message TEXT
        )
    ''')
    
    # 创建索引
    c.execute('''
        CREATE INDEX IF NOT EXISTS idx_task_queue_status 
        ON task_queue(status)
    ''')
    c.execute('''
        CREATE INDEX IF NOT EXISTS idx_task_queue_priority 
        ON task_queue(priority)
    ''')
    
    # 6. Worker状态表
    c.execute('''
        CREATE TABLE IF NOT EXISTS worker_status (
            worker_id TEXT PRIMARY KEY,
            status TEXT DEFAULT 'idle',
            current_task TEXT,
            last_heartbeat TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            cpu_usage REAL DEFAULT 0,
            memory_usage REAL DEFAULT 0,
            tasks_processed INTEGER DEFAULT 0,
            tasks_failed INTEGER DEFAULT 0
        )
    ''')
    
    conn.commit()
    conn.close()
    
    print("✅ 管理员后台表初始化完成")


def seed_default_data(db_path: str):
    """插入默认数据"""
    
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # 默认系统配置
    default_configs = [
        ('site_name', 'Kanban Admin', 'string', '站点名称'),
        ('site_description', '任务管理系统', 'string', '站点描述'),
        ('max_login_attempts', '5', 'int', '最大登录尝试次数'),
        ('session_timeout', '3600', 'int', '会话超时时间(秒)'),
        ('enable_registration', 'true', 'bool', '是否允许注册'),
        ('maintenance_mode', 'false', 'bool', '维护模式'),
        ('log_retention_days', '30', 'int', '日志保留天数'),
        ('email_notification', 'true', 'bool', '启用邮件通知'),
    ]
    
    for key, value, type_, desc in default_configs:
        c.execute('''
            INSERT OR IGNORE INTO system_config (config_key, config_value, config_type, description)
            VALUES (?, ?, ?, ?)
        ''', (key, value, type_, desc))
    
    # 默认邮件模板
    default_templates = [
        (
            'welcome_email',
            '欢迎加入 {site_name}',
            '''<h2>欢迎加入 {site_name}!</h2>
<p>亲爱的 {username}，</p>
<p>感谢您注册 {site_name}。您的账户已创建成功。</p>
<p>如有任何问题，请联系管理员。</p>
<p>祝您使用愉快！</p>''',
            json.dumps(['site_name', 'username'])
        ),
        (
            'password_reset',
            '密码重置请求',
            '''<h2>密码重置</h2>
<p>您收到了这封邮件是因为有人请求重置您的账户密码。</p>
<p>请点击以下链接重置密码：</p>
<p><a href="{reset_link}">重置密码</a></p>
<p>此链接将在 {expiry_hours} 小时后失效。</p>
<p>如果您没有请求重置密码，请忽略此邮件。</p>''',
            json.dumps(['reset_link', 'expiry_hours'])
        ),
        (
            'task_assigned',
            '新任务分配通知',
            '''<h2>新任务分配</h2>
<p>您被分配了一个新任务：</p>
<h3>{task_title}</h3>
<p>{task_description}</p>
<p>截止日期：{due_date}</p>
<p>优先级：{priority}</p>''',
            json.dumps(['task_title', 'task_description', 'due_date', 'priority'])
        ),
        (
            'system_alert',
            '系统警报',
            '''<h2>系统警报</h2>
<p><strong>警报级别：</strong> {alert_level}</p>
<p><strong>警报类型：</strong> {alert_type}</p>
<p><strong>消息：</strong></p>
<p>{message}</p>
<p><strong>时间：</strong> {timestamp}</p>''',
            json.dumps(['alert_level', 'alert_type', 'message', 'timestamp'])
        ),
    ]
    
    for name, subject, body, variables in default_templates:
        c.execute('''
            INSERT OR IGNORE INTO email_templates (template_name, subject, body, variables)
            VALUES (?, ?, ?, ?)
        ''', (name, subject, body, variables))
    
    conn.commit()
    conn.close()
    
    print("✅ 默认数据插入完成")


def migrate_users_table(db_path: str):
    """迁移用户表，添加必要的字段"""
    
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # 检查users表是否存在
    c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    if not c.fetchone():
        # 创建users表
        c.execute('''
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT DEFAULT 'user',
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP
            )
        ''')
        print("✅ users表创建完成")
    else:
        # 检查并添加缺失的列
        c.execute("PRAGMA table_info(users)")
        existing_columns = [row[1] for row in c.fetchall()]
        
        if 'role' not in existing_columns:
            c.execute("ALTER TABLE users ADD COLUMN role TEXT DEFAULT 'user'")
            print("✅ users表添加role列")
        
        if 'status' not in existing_columns:
            c.execute("ALTER TABLE users ADD COLUMN status TEXT DEFAULT 'active'")
            print("✅ users表添加status列")
        
        if 'last_login' not in existing_columns:
            c.execute("ALTER TABLE users ADD COLUMN last_login TIMESTAMP")
            print("✅ users表添加last_login列")
    
    conn.commit()
    conn.close()


def init_admin_system(db_path: str = None):
    """初始化整个管理员系统"""
    
    if db_path is None:
        db_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            '..', 'backend', 'kanban_v5.db'
        )
    
    print(f"🚀 初始化管理员后台系统...")
    print(f"📁 数据库路径: {db_path}")
    
    # 确保目录存在
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    # 初始化表
    init_admin_tables(db_path)
    
    # 迁移用户表
    migrate_users_table(db_path)
    
    # 插入默认数据
    seed_default_data(db_path)
    
    print("✅ 管理员后台系统初始化完成！")


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    else:
        db_path = None
    
    init_admin_system(db_path)
