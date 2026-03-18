import os
import re

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

# 数据库配置
DB_TYPE = env.get('DB_TYPE', 'sqlite')

class MySQLRow:
    """MySQL 行对象，模拟 sqlite3.Row 的行为"""
    def __init__(self, cursor, row):
        self._cursor = cursor
        self._row = row
        self._keys = [desc[0] for desc in cursor.description]
    
    def __getitem__(self, key):
        if isinstance(key, int):
            return self._row[key]
        elif isinstance(key, str):
            try:
                idx = self._keys.index(key)
                return self._row[idx]
            except ValueError:
                raise KeyError(key)
        else:
            raise TypeError("Invalid key type")
    
    def __iter__(self):
        return iter(self._keys)
    
    def keys(self):
        return self._keys
    
    def __len__(self):
        return len(self._row)

class MySQLCursorWrapper:
    """MySQL Cursor 包装器，返回兼容的行对象"""
    def __init__(self, cursor):
        self._cursor = cursor
        self.description = cursor.description
    
    def execute(self, query, params=None):
        return self._cursor.execute(query, params)
    
    def fetchone(self):
        row = self._cursor.fetchone()
        if row is None:
            return None
        return MySQLRow(self._cursor, row)
    
    def fetchall(self):
        rows = self._cursor.fetchall()
        return [MySQLRow(self._cursor, row) for row in rows]
    
    def __getattr__(self, name):
        return getattr(self._cursor, name)

class MySQLConnectionWrapper:
    """MySQL 连接包装器"""
    def __init__(self, conn):
        self._conn = conn
    
    def cursor(self):
        return MySQLCursorWrapper(self._conn.cursor())
    
    def commit(self):
        return self._conn.commit()
    
    def close(self):
        return self._conn.close()
    
    def __getattr__(self, name):
        return getattr(self._conn, name)

if DB_TYPE == 'mysql':
    import pymysql
    MYSQL_HOST = env.get('MYSQL_HOST', 'localhost')
    MYSQL_PORT = int(env.get('MYSQL_PORT', 3306))
    MYSQL_USER = env.get('MYSQL_USER', 'root')
    MYSQL_PASSWORD = env.get('MYSQL_PASSWORD', '')
    MYSQL_DATABASE = env.get('MYSQL_DATABASE', 'kanban')
    
    def get_db_connection():
        conn = pymysql.connect(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE,
            charset='utf8mb4'
        )
        return MySQLConnectionWrapper(conn)
    
    def get_db_cursor(conn):
        return conn.cursor()
        
else:
    # SQLite 配置
    import sqlite3
    DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'kanban_v5.db')
    
    def get_db_connection():
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        return conn
    
    def get_db_cursor(conn):
        return conn.cursor()
