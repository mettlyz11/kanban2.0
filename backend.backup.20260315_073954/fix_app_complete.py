#!/usr/bin/env python3
"""
完整修复 app.py - 恢复原始版本并应用最小修改
"""

import re

# 读取损坏的文件
with open('/opt/kanban-react/backend/app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 修复导入 - 添加 pymysql
if 'import pymysql' not in content:
    content = content.replace('import sqlite3', 'import sqlite3\nimport pymysql')

# 2. 完全替换 get_db 函数
old_pattern = r'def get_db\(\):.*?(?=\ndef |\Z)'
new_get_db = '''def get_db():
    """获取数据库连接 - 使用 RDS MySQL"""
    import pymysql
    conn = pymysql.connect(
        host='rm-2zew4su9p966e8x2ofo.mysql.rds.aliyuncs.com',
        port=3306,
        user='kanban',
        password='Irc210Irc210!',
        database='kanban',
        charset='utf8mb4'
    )
    return conn

'''

content = re.sub(old_pattern, new_get_db, content, flags=re.DOTALL)

# 写入文件
with open('/opt/kanban-react/backend/app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ app.py 已修复")

# 验证语法
import subprocess
result = subprocess.run(['python3', '-m', 'py_compile', '/opt/kanban-react/backend/app.py'], 
                       capture_output=True, text=True)
if result.returncode == 0:
    print("✅ 语法检查通过")
else:
    print(f"❌ 语法错误：{result.stderr}")
