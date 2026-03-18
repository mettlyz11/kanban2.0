#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库配置 - 纯 MySQL/RDS 版本

版本：v2.4.13 (2026-03-18)
说明：已移除 SQLite 支持，仅使用 MySQL/RDS
"""

import os
import pymysql
from typing import Optional

# 读取 .env 文件
def load_env():
    env = {}
    try:
        with open(os.path.join(os.path.dirname(__file__), '.env'), 'r') as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    env[key] = value
    except:
        pass
    return env

env = load_env()

# MySQL/RDS 配置
MYSQL_CONFIG = {
    'host': env.get('MYSQL_HOST', 'rm-2zew4su9p966e8x2ofo.mysql.rds.aliyuncs.com'),
    'port': int(env.get('MYSQL_PORT', '3306')),
    'user': env.get('MYSQL_USER', 'kanban'),
    'password': env.get('MYSQL_PASSWORD', ''),
    'database': env.get('MYSQL_DATABASE', 'kanban'),
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor,
    'autocommit': False,
}

def get_connection():
    """获取 MySQL 数据库连接"""
    config = MYSQL_CONFIG.copy()
    config['password'] = os.environ.get('MYSQL_PASSWORD', config['password'])
    return pymysql.connect(**config)

def get_db_info():
    """获取数据库信息"""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()['VERSION()']
        
        cursor.execute("SELECT DATABASE()")
        database = cursor.fetchone()['DATABASE()']
        
        cursor.close()
        conn.close()
        
        return {
            'type': 'MySQL',
            'version': version,
            'database': database,
            'host': MYSQL_CONFIG['host'],
        }
    except Exception as e:
        return {
            'type': 'MySQL',
            'error': str(e),
        }

__all__ = ['MYSQL_CONFIG', 'get_connection', 'get_db_info']
