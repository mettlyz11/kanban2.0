#!/usr/bin/env python3
"""
数据库配置模块 - 纯 MySQL/RDS 支持
已移除 SQLite 支持，仅使用阿里云 RDS
"""

import os
import pymysql
from contextlib import contextmanager
from typing import Optional, Any, List, Tuple, Union
import logging

logger = logging.getLogger(__name__)

# ============================================
# MySQL/RDS 配置
# ============================================
MYSQL_CONFIG = {
    'host': os.environ.get('MYSQL_HOST', 'rm-2zew4su9p966e8x2o.mysql.rds.aliyuncs.com'),
    'port': int(os.environ.get('MYSQL_PORT', '3306')),
    'user': os.environ.get('MYSQL_USER', 'kanban'),
    'password': os.environ.get('MYSQL_PASSWORD', ''),
    'database': os.environ.get('MYSQL_DATABASE', 'kanban'),
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor,
    'autocommit': False,
}

# ============================================
# 连接管理
# ============================================

@contextmanager
def get_db_connection():
    """
    获取 MySQL 数据库连接（上下文管理器）
    """
    config = MYSQL_CONFIG.copy()
    config['password'] = os.environ.get('MYSQL_PASSWORD', '')
    conn = pymysql.connect(**config)
    try:
        yield conn
    finally:
        conn.close()

@contextmanager
def get_db_cursor():
    """
    获取数据库游标（上下文管理器）
    自动处理提交和回滚
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            yield cursor
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()

def execute_query(sql: str, params: Optional[Union[Tuple, List, dict]] = None) -> List[dict]:
    """
    执行查询并返回结果列表
    """
    with get_db_connection() as conn:
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        try:
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            return cursor.fetchall()
        finally:
            cursor.close()

def execute_update(sql: str, params: Optional[Union[Tuple, List, dict]] = None) -> int:
    """
    执行更新操作并返回受影响的行数
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            if params:
                cursor.execute(sql, params)
            else:
                cursor.execute(sql)
            conn.commit()
            return cursor.rowcount
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            cursor.close()

def get_db_info() -> dict:
    """
    获取数据库连接信息
    """
    return {
        'mysql_host': MYSQL_CONFIG['host'],
        'mysql_port': MYSQL_CONFIG['port'],
        'mysql_user': MYSQL_CONFIG['user'],
        'mysql_database': MYSQL_CONFIG['database'],
    }

def table_exists(table_name: str) -> bool:
    """
    检查表是否存在
    """
    sql = "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = %s AND table_name = %s"
    result = execute_query(sql, (MYSQL_CONFIG['database'], table_name))
    return result[0]['COUNT(*)'] > 0
