#!/usr/bin/env python3
import os
from lib.db_connector import get_db_connection

conn = get_db_connection()
c = conn.cursor()

file_path = '/Users/mettlyz/.openclaw/workspace/output/task-2080/AI材料科学行业2026年Q2融资情报分析报告.md'
file_size = os.path.getsize(file_path)

c.execute('''INSERT INTO attachments 
    (entity_type, entity_id, filename, url, size, file_type, created_at) 
    VALUES (%s, %s, %s, %s, %s, %s, NOW())''',
    ('task', 2080, 'AI材料科学行业2026年Q2融资情报分析报告.md', 
     f'output/task-2080/AI材料科学行业2026年Q2融资情报分析报告.md', 
     file_size, 'md'))

conn.commit()
conn.close()
# print(f'✅ 附件已上传: AI材料科学行业2026年Q2融资情报分析报告.md ({file_size} bytes)')
