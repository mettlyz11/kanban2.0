#!/usr/bin/env python3
import mysql.connector
config = {
    'host': 'rm-2zew4su9p966e8x2ofo.mysql.rds.aliyuncs.com',
    'port': 3306,
    'user': 'kanban',
    'password': 'Irc210Irc210!',
    'database': 'kanban',
}
conn = mysql.connector.connect(**config)
cursor = conn.cursor(dictionary=True)

time_condition = 'DATE_SUB(NOW(), INTERVAL 24 HOUR)'
sql = f'''SELECT id, cpu_percent as cpu, memory_percent as memory, disk_percent as disk, timestamp 
          FROM system_metrics 
          WHERE timestamp >= {time_condition} 
          ORDER BY timestamp ASC'''
print('SQL:', sql)
print()

try:
    cursor.execute(sql)
    rows = cursor.fetchall()
    print(f'查到 {len(rows)} 条记录:\n')
    for i, r in enumerate(rows[-10:]):
        print(f'  {i+1}. {r["timestamp"]} - CPU: {r["cpu"]}% 内存: {r["memory"]}% 磁盘: {r["disk"]}%')
    conn.close()
except Exception as e:
    print(f'错误: {e}')
    import traceback
    traceback.print_exc()
