#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, '/Users/mettlyz/.openclaw/workspace/scripts')

import pymysql
from lib.db_connector import get_db_connection

# 文件列表
files = [
    {
        'name': '关于推动AI+新材料在长江流域生态保护中应用的建议_提案_2026-04-22.md',
        'path': '/Users/mettlyz/.openclaw/workspace/output/task-1541/关于推动AI+新材料在长江流域生态保护中应用的建议_提案_2026-04-22.md',
        'type': 'md'
    },
    {
        'name': '关于建立材料碳足迹核算与碳普惠联动机制的建议_提案_2026-04-22.md',
        'path': '/Users/mettlyz/.openclaw/workspace/output/task-1541/关于建立材料碳足迹核算与碳普惠联动机制的建议_提案_2026-04-22.md',
        'type': 'md'
    },
    {
        'name': '致公党海淀区活动参与计划_Q2_2026_活动计划_2026-04-22.md',
        'path': '/Users/mettlyz/.openclaw/workspace/output/task-1541/致公党海淀区活动参与计划_Q2_2026_活动计划_2026-04-22.md',
        'type': 'md'
    }
]

conn = get_db_connection()
c = conn.cursor()

for f in files:
    size = os.path.getsize(f['path'])
    url = f'output/task-1541/{f["name"]}'
    c.execute('''INSERT INTO attachments 
        (entity_type, entity_id, filename, url, size, file_type) 
        VALUES (%s, %s, %s, %s, %s, %s)''',
        ('task', 1541, f['name'], url, size, f['type']))
    # print(f'✅ 插入附件: {f["name"]}')

conn.commit()
conn.close()
# print('所有附件已插入数据库')