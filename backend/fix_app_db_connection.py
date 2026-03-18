#!/usr/bin/env python3
"""
修复 app.py 中的数据库连接问题
"""

# 读取文件
with open('/opt/kanban-react/backend/app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 修复 get_db 函数 - 直接返回连接，不使用上下文管理器
old_get_db = """def get_db():
    \"\"\"获取数据库连接（兼容旧代码）\"\"\"
    conn = get_db_connection()
    # 为了兼容，返回连接对象而不是上下文
    # 调用者需要手动管理连接生命周期
    return conn"""

new_get_db = """def get_db():
    \"\"\"获取数据库连接（兼容旧代码）\"\"\"
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
    return conn"""

content = content.replace(old_get_db, new_get_db)

# 替换所有 .__enter__() 调用
content = content.replace('get_db_connection().__enter__()', 'get_db()')

# 写入文件
with open('/opt/kanban-react/backend/app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ 修复完成！")
