#!/usr/bin/env python3
import os
import sys
sys.path.insert(0, '/Users/mettlyz/.openclaw/workspace/scripts')
from lib.db_connector import get_db_connection

conn = get_db_connection()
c = conn.cursor()

output_dir = '/Users/mettlyz/.openclaw/workspace/output/task-2077'
files_to_upload = [
    '高强度工作个性化健康管理方案_刘宇宙_2026-04-26.md',
    '健康管理方案_30天启动清单_2026-04-26.md',
    '高强度工作下健康维护方案_刘宇宙_2026-04-26.md',
    '高强度工作健康维护方案_20260426.md',
    '身体健康与精力管理_健康管理方案_2026-04-25.md',
]

# Clear existing attachments for this task first
c.execute('DELETE FROM attachments WHERE entity_type=%s AND entity_id=%s', ('task', 2077))
print(f'已清除任务2077的 {c.rowcount} 条旧附件记录')

# Upload each file
for filename in files_to_upload:
    file_path = os.path.join(output_dir, filename)
    if os.path.exists(file_path):
        file_size = os.path.getsize(file_path)
        c.execute('''INSERT INTO attachments 
            (entity_type, entity_id, filename, url, size, file_type) 
            VALUES (%s, %s, %s, %s, %s, %s)''',
            ('task', 2077, filename, 
             f'output/task-2077/{filename}', 
             file_size, 'md'))
        print(f'✅ 附件已上传: {filename} ({file_size} bytes)')
    else:
        print(f'⚠️ 文件不存在，跳过: {filename}')

conn.commit()
conn.close()
print('\n所有附件上传完成！')
