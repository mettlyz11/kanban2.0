#!/usr/bin/env python3
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

# 兼容性支持 - 避免导入错误
SQLITE_DB_PATH = '/opt/kanban-react/backend/kanban_v5.db'

# 兼容性函数
def execute_query(query, params=None, fetch=True):
    '''执行查询（兼容旧代码）'''
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            if fetch:
                return cursor.fetchall()
            conn.commit()
            return None

def execute_update(query, params=None):
    '''执行更新（兼容旧代码）'''
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            conn.commit()
            return cursor.rowcount

def table_exists(table_name):
    '''检查表是否存在'''
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute('SHOW TABLES LIKE %s', (table_name,))
            return cursor.fetchone() is not None

def get_db_info():
    '''获取数据库信息'''
    return {
        'type': DB_TYPE,
        'host': DB_CONFIG['host'],
        'database': DB_CONFIG['database']
    }
