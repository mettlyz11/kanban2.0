#!/usr/bin/env python3
import pymysql

config = {
    "host": "rm-2zew4su9p966e8x2ofo.mysql.rds.aliyuncs.com",
    "port": 3306,
    "user": "kanban",
    "password": "Irc210Irc210!",
    "database": "kanban",
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
}

print("测试 /api/system/history 的SQL...")
conn = pymysql.connect(**config)
cursor = conn.cursor()

sql = '''
    SELECT id, cpu_percent, memory_percent, disk_percent, status, timestamp as created_at
    FROM system_metrics
    ORDER BY timestamp DESC
    LIMIT 50
'''

print(f"SQL: {sql}")
print()

try:
    cursor.execute(sql)
    rows = cursor.fetchall()
    print(f"查询成功！返回 {len(rows)} 条记录:\n")
    for i, r in enumerate(rows[:10]):
        print(f"  {i+1}. id={r['id']}, cpu={r['cpu_percent']}, memory={r['memory_percent']}, created_at={r['created_at']}")
    
    conn.close()
except Exception as e:
    print(f"错误: {e}")
    import traceback
    traceback.print_exc()
