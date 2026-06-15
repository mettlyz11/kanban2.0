import os
import pymysql

base = '/Users/mettlyz/.openclaw/workspace/output/task-1331'
files = [
    'T1T2滞后根因审计报告_2026-04-22.md',
    '资源重配执行手册_2026-04-22.md',
    '权重优先级对齐看板V1_2026-04-22.md',
]

conn = pymysql.connect(
    host='rm-2zew4su9p966e8x2ofo.mysql.rds.aliyuncs.com',
    user='kanban', password='Irc210Irc210!',
    database='kanban', charset='utf8mb4'
)
c = conn.cursor()
for fn in files:
    path = os.path.join(base, fn)
    size = os.path.getsize(path)
    c.execute('''INSERT INTO attachments 
        (entity_type, entity_id, filename, url, size, file_type) 
        VALUES (%s, %s, %s, %s, %s, %s)''',
        ('task', 1331, fn, f'output/task-1331/{fn}', size, 'md'))
conn.commit()
conn.close()
# print('附件记录已插入')
