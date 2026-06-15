#!/usr/bin/env python3
import os, pymysql
from datetime import datetime

pw = open('/opt/kanban-react/backend/.env').read().split('MYSQL_PASSWORD=')[1].split('\n')[0].strip()
conn = pymysql.connect(host='rm-2zew4su9p966e8x2ofo.mysql.rds.aliyuncs.com', port=3306, user='kanban', password=pw, database='kanban', charset='utf8mb4')
with conn.cursor() as cur:
    cur.execute('DELETE FROM perception_events WHERE created_at < NOW() - INTERVAL 30 DAY')
    n = cur.rowcount
    conn.commit()
# print(f'[{datetime.now()}] cleaned {n} perception_events')
