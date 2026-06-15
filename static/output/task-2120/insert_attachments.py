#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, '/Users/mettlyz/.openclaw/workspace/scripts')

from lib.db_connector import get_db_connection

conn = get_db_connection()
c = conn.cursor()

files = [
    ('AI半导体材料概念股2026年Q2财报前瞻与持仓优化方案_20260426.md', 4115),
    ('多因子评级矩阵_20260426.md', 1960),
    ('Q2持仓优化建议书_20260426.md', 1882),
    ('个股买入卖出时机建议_20260426.md', 2212),
]

for filename, size in files:
    c.execute('''INSERT INTO attachments 
        (entity_type, entity_id, filename, url, size, file_type, created_at) 
        VALUES (%s, %s, %s, %s, %s, %s, NOW())''',
        ('task', 2120, filename, 
         f'output/task-2120/{filename}', 
         size, 'md'))
    # print(f'已插入附件: {filename}')

conn.commit()
conn.close()
# print('所有附件已成功插入数据库')
