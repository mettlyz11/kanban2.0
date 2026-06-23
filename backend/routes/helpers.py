"""Shared helpers for route blueprints"""
import os
import json
import pymysql
from pymysql.cursors import DictCursor
from datetime import datetime

def get_db():
    """获取 MySQL 数据库连接"""
    config = {
        "host": os.environ.get("MYSQL_HOST", "rm-2zew4su9p966e8x2ofo.mysql.rds.aliyuncs.com"),
        "port": int(os.environ.get("MYSQL_PORT", "3306")),
        "user": os.environ.get("MYSQL_USER", "kanban"),
        "password": os.environ.get("MYSQL_PASSWORD", ""),
        "database": os.environ.get("MYSQL_DATABASE", "kanban"),
        "charset": "utf8mb4",
        "cursorclass": DictCursor,
        "autocommit": False,
        "connect_timeout": 3,
        "read_timeout": 10,
    }
    return pymysql.connect(**config)

def row_to_dict(row, cursor):
    if row is None:
        return None
    
    # 统一处理：无论是 dict 还是 tuple，都转成标准 dict
    import json
    if isinstance(row, dict):
        result = dict(row)
    elif hasattr(cursor, "description") and cursor.description:
        columns = [desc[0] for desc in cursor.description]
        result = dict(zip(columns, row))
    else:
        return row
    
    # 🌟 自动解析 JSON 描述
    desc = result.get('description', '')
    if desc and isinstance(desc, str) and desc.startswith('{'):
        try:
            parsed = json.loads(desc)
            result['json_description'] = parsed
            # text_description: 只显示目标+步骤+验收,不显示上下文文件列表
            _goal = parsed.get('goal', '')
            _steps = '\n'.join(f'{i+1}. {s}' for i,s in enumerate(parsed.get('steps', []))) if parsed.get('steps') else ''
            _accept = parsed.get('acceptance', '')
            _clean = f'【目标】{_goal}\n【步骤】\n{_steps}\n【验收】{_accept}'
            result['text_description'] = _clean or desc
        except json.JSONDecodeError:
            result['json_description'] = None
            result['text_description'] = desc
    else:
        result['json_description'] = None
        result['text_description'] = desc if desc else ''
    
    return result

