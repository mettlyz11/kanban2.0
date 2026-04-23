#!/usr/bin/env python3
"""
修复 app.py - 添加 dotenv 加载
"""

# 读取文件
with open('/opt/kanban-react/backend/app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 在 import os 后添加 dotenv 加载
old_imports = """from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import pymysql
import os
import json
import logging
from datetime import datetime
from functools import wraps
from database_config import get_db_connection, DB_TYPE"""

new_imports = """from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import pymysql
import os
import json
import logging
from datetime import datetime
from functools import wraps
from dotenv import load_dotenv
from database_config import get_db_connection, DB_TYPE

# 加载环境变量
load_dotenv()"""

content = content.replace(old_imports, new_imports)

# 写入文件
with open('/opt/kanban-react/backend/app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ 已添加 dotenv 加载")
