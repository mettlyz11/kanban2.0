#!/usr/bin/env python3
"""
数据库配置模块 - MySQL/RDS 版本
"""

import os
import pymysql
from contextlib import contextmanager

# MySQL/RDS 配置
MYSQL_CONFIG = {
    'host': os.environ.get('MYSQL_HOST', 'rm-2zew4su9p966e8x2ofo.mysql.rds.aliyuncs.com'),
    'port': int(os.environ.get('MYSQL_PORT', '3306')),
    'user': os.environ.get('MYSQL_USER', 'kanban'),
    'password': os.environ.get('MYSQL_PASSWORD', ''),
    'database': os.environ.get('MYSQL_DATABASE', 'kanban'),
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor,
    'autocommit': False,
}

# 数据库类型定义
DB_TYPE = 'mysql'

@contextmanager
def get_db_connection():
    """获取 MySQL 数据库连接"""
    config = MYSQL_CONFIG.copy()
    config['password'] = os.environ.get('MYSQL_PASSWORD', '')
    conn = pymysql.connect(**config)
    try:
        yield conn
    finally:
        conn.close()

@contextmanager
def get_db_cursor():
    """获取数据库游标（上下文管理器）"""
    config = MYSQL_CONFIG.copy()
    config['password'] = os.environ.get('MYSQL_PASSWORD', '')
    conn = pymysql.connect(**config)
    cursor = conn.cursor()
    try:
        yield cursor
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        cursor.close()
        conn.close()

# 兼容旧代码的别名
get_mysql_connection = get_db_connection

def execute_query(sql, params=None):
    """执行查询并返回结果"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params or ())
        return cursor.fetchall()

def execute_update(sql, params=None):
    """执行更新操作（INSERT/UPDATE/DELETE）"""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(sql, params or ())
        conn.commit()
        return cursor.rowcount

def table_exists(table_name):
    """检查表是否存在"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SHOW TABLES LIKE %s", (table_name,))
            return cursor.fetchone() is not None
    except:
        return False


def get_db_info():
    """Get database connection info"""
    return {
        "mysql_host": MYSQL_CONFIG["host"],
        "mysql_port": MYSQL_CONFIG["port"],
        "mysql_user": MYSQL_CONFIG["user"],
        "mysql_database": MYSQL_CONFIG["database"]
    }


def row_to_dict(row, cursor):
    """Convert row data to dict, compatible with SQLite and MySQL"""
    if row is None:
        return None
    if isinstance(row, dict):
        return row
    # Tuple case, get column names from cursor
    if hasattr(cursor, 'description') and cursor.description:
        columns = [desc[0] for desc in cursor.description]
        return dict(zip(columns, row))
    return {}
