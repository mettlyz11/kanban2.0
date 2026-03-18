#!/usr/bin/env python3
"""
在服务器上直接修改 app.py，使其使用 RDS
"""

import re

# 读取文件
with open('/opt/kanban-react/backend/app.py', 'r', encoding='utf-8') as f:
    content = f.read()

print(f"原文件大小：{len(content)} 字节 ({len(content.splitlines())} 行)")

# 1. 替换导入语句
old_imports = """from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3
import os
import json
import logging
from datetime import datetime
from functools import wraps"""

new_imports = """from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import pymysql
import os
import json
import logging
from datetime import datetime
from functools import wraps
from database_config import get_db_connection, DB_TYPE"""

content = content.replace(old_imports, new_imports)

# 2. 删除或注释掉 DB_PATH 定义
content = re.sub(
    r"^DB_PATH = .*\n",
    "# DB_PATH = 'kanban_v5.db'  # 已迁移到 RDS\n",
    content,
    flags=re.MULTILINE
)

# 3. 替换 get_db 函数
old_get_db = """def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn"""

new_get_db = """def get_db():
    \"\"\"获取数据库连接（兼容旧代码）\"\"\"
    conn = get_db_connection()
    # 为了兼容，返回连接对象而不是上下文
    # 调用者需要手动管理连接生命周期
    return conn"""

content = content.replace(old_get_db, new_get_db)

# 4. 替换所有直接的 sqlite3.connect 调用
count = 0
def replace_sqlite_connect(match):
    global count
    count += 1
    indent = match.group(1)
    return f"{indent}conn = get_db_connection().__enter__()  # RDS"

content = re.sub(
    r"^(\s+)conn = sqlite3\.connect\(DB_PATH\)",
    replace_sqlite_connect,
    content,
    flags=re.MULTILINE
)

print(f"替换了 {count} 处 sqlite3.connect 调用")

# 写入文件
with open('/opt/kanban-react/backend/app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print(f"✅ 修改完成！新文件大小：{len(content)} 字节")
print(f"✅ 现在 app.py 使用 RDS MySQL 数据库")
