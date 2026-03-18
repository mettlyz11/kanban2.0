#!/usr/bin/env python3
"""
修复 database_config.py - 硬编码 RDS 配置
"""

content = '''#!/usr/bin/env python3
"""
数据库配置 - 硬编码 RDS 配置（生产环境）
"""

import os
import pymysql
from contextlib import contextmanager

# 生产环境 RDS 配置（硬编码，避免环境变量问题）
DB_CONFIG = {
    'host': 'rm-2zew4su9p966e8x2ofo.mysql.rds.aliyuncs.com',
    'port': 3306,
    'user': 'kanban',
    'password': 'Irc210Irc210!',
    'database': 'kanban',
    'charset': 'utf8mb4'
}

DB_TYPE = 'mysql'  # 固定使用 MySQL

@contextmanager
def get_db_connection():
    """获取数据库连接（上下文管理器）"""
    conn = None
    try:
        conn = pymysql.connect(**DB_CONFIG)
        yield conn
    finally:
        if conn:
            conn.close()

def get_db_cursor():
    """获取数据库游标（兼容旧代码）"""
    conn = pymysql.connect(**DB_CONFIG)
    return conn, conn.cursor()
'''

with open('/opt/kanban-react/backend/database_config.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ database_config.py 已修复 - 使用硬编码 RDS 配置")
