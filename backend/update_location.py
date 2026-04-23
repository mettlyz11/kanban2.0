#!/usr/bin/env python3
import pymysql

conn = pymysql.connect(
    host='rm-2zew4su9p966e8x2ofo.mysql.rds.aliyuncs.com',
    user='kanban',
    password='Irc210Irc210!',
    database='kanban',
    port=3306,
    charset='utf8mb4'
)
c = conn.cursor()
# 找到刚才添加的事件ID
c.execute("SELECT id FROM calendar_events WHERE title LIKE '%北京高端科学仪器%'")
result = c.fetchone()
if result:
    event_id = result[0]
    sql = 'UPDATE calendar_events SET location = %s WHERE id = %s'
    data = ('中关村自主创新示范区展示交易中心会议中心百望山厅（海淀区新建宫门路2号）', event_id)
    c.execute(sql, data)
    conn.commit()
    print(f'✓ 已更新事件 {event_id} 的地点信息')
    print('新地点: 中关村自主创新示范区展示交易中心百望山厅（海淀区新建宫门路2号）')
conn.close()
