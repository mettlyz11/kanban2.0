#!/usr/bin/env python3
import sqlite3
import pymysql

# 检查 SQLite 表结构
sqlite_conn = sqlite3.connect('/opt/kanban-react/backend/kanban_v5.db')
sqlite_c = sqlite_conn.cursor()

# 连接 RDS
mysql_conn = pymysql.connect(
    host='rm-2zew4su9p966e8x2ofo.mysql.rds.aliyuncs.com',
    port=3306,
    user='kanban',
    password='Irc210Irc210!',
    database='kanban',
    charset='utf8mb4'
)
mysql_c = mysql_conn.cursor()

# 需要修复的表
tables_to_fix = ['meetings', 'tasks', 'projects', 'calendar_events', 'user_profiles']

for table in tables_to_fix:
    print(f"\n{'='*60}")
    print(f"表：{table}")
    print('='*60)
    
    try:
        # SQLite 结构
        sqlite_c.execute(f"PRAGMA table_info({table})")
        cols = sqlite_c.fetchall()
        print(f"\nSQLite 结构:")
        for col in cols:
            print(f"  {col[1]:25} type={str(col[2]):15} pk={col[5]}")
        
        # 获取数据量
        sqlite_c.execute(f"SELECT COUNT(*) FROM {table}")
        count = sqlite_c.fetchone()[0]
        print(f"数据量：{count} 条")
        
        # 检查 RDS 中是否存在
        mysql_c.execute("SHOW TABLES LIKE %s", (table,))
        exists = mysql_c.fetchone()
        print(f"RDS 中是否存在：{'是' if exists else '否'}")
        
    except Exception as e:
        print(f"错误：{e}")

sqlite_conn.close()
mysql_conn.close()
