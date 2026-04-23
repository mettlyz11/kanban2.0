#!/usr/bin/env python3
import pymysql
import uuid

conn = pymysql.connect(
    host='rm-2zew4su9p966e8x2ofo.mysql.rds.aliyuncs.com',
    user='kanban',
    password='Irc210Irc210!',
    database='kanban',
    port=3306,
    charset='utf8mb4'
)
c = conn.cursor()
event_id = str(uuid.uuid4())
sql = '''
INSERT INTO calendar_events (id, title, description, start_time, end_time, location, is_all_day, category)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
'''
data = (
    event_id,
    '北京高端科学仪器发展对接会',
    '北京高端科学仪器发展对接会议程：1.北京冷冻电镜产业落地工作对接 2.AI+科学仪器工作对接',
    '2026-04-09 14:30:00',
    '2026-04-09 17:00:00',
    '中关村自主创新示范区展示交易中心会议中心（海淀区新建宫门路2号）',
    0,
    'meeting'
)
c.execute(sql, data)
conn.commit()
print(f'✓ 已添加到看板数据库: ID={event_id}')
print(f'  标题: 北京高端科学仪器发展对接会')
print(f'  时间: 2026-04-09 14:30-17:00')
print(f'  地点: 中关村自主创新示范区展示交易中心')
conn.close()
