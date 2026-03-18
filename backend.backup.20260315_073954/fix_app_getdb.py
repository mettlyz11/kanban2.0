#!/usr/bin/env python3
"""
修复 app.py 中的 get_db 函数
"""

with open('/opt/kanban-react/backend/app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 替换 get_db 函数为简单版本
old_get_db = '''def get_db():
    """获取数据库连接（兼容旧代码）"""
    if DB_TYPE == 'sqlite':
        import sqlite3
        conn = sqlite3.connect('kanban_v5.db')
        conn.row_factory = sqlite3.Row
    else:
        conn = pymysql.connect(
            host='rm-2zew4su9p966e8x2ofo.mysql.rds.aliyuncs.com',
            port=3306,
            user='kanban',
            password='Irc210Irc210!',
            database='kanban',
            charset='utf8mb4'
        )
    return conn'''

new_get_db = '''def get_db():
    """获取数据库连接（兼容旧代码）"""
    from database_config import get_db_cursor
    conn, cursor = get_db_cursor()
    # 存储连接对象以便后续关闭
    cursor._connection = conn
    return cursor'''

content = content.replace(old_get_db, new_get_db)

# 移除 dotenv 导入（不需要了）
content = content.replace('from dotenv import load_dotenv\n\n# 加载环境变量\nload_dotenv()\n', '')

with open('/opt/kanban-react/backend/app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ app.py 已修复")
