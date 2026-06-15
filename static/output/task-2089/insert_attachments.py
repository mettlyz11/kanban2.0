#!/usr/bin/env python3
import os
import sys
sys.path.insert(0, '/Users/mettlyz/.openclaw/workspace/scripts')
from lib.db_connector import get_db_connection

conn = get_db_connection()
c = conn.cursor()

files = [
    '化工行业数字化转型需求分析报告_20260426.md',
    'Top20潜在客户优先级评分表_20260426.md',
    '客户切入策略与业务机会清单_20260426.md'
]

for filename in files:
    file_path = '/Users/mettlyz/.openclaw/workspace/output/task-2089/' + filename
    file_size = os.path.getsize(file_path)
    
    sql = "INSERT INTO attachments (entity_type, entity_id, filename, url, size, file_type, created_at) VALUES (%s, %s, %s, %s, %s, %s, NOW())"
    c.execute(sql, ('task', 2089, filename, 'output/task-2089/' + filename, file_size, 'md'))
    # print(f'✅ 附件已上传: {filename} ({file_size} bytes)')

conn.commit()
conn.close()
# print('🎉 所有附件已成功插入数据库')
