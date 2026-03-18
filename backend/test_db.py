#!/usr/bin/env python3
import pymysql

try:
    conn = pymysql.connect(
        host='rm-2zew4su9p966e8x2ofo.mysql.rds.aliyuncs.com',
        port=3306,
        user='kanban',
        password='Irc210Irc210!',
        database='kanban',
        connect_timeout=10
    )
    print('✅ 数据库连接成功')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) as count FROM tasks')
    result = cursor.fetchone()
    print(f'✅ tasks 表中有 {result["count"]} 条记录')
    conn.close()
except Exception as e:
    print(f'❌ 连接失败：{e}')
