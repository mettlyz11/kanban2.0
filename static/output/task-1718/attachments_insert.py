import os
import sys
sys.path.append('/Users/mettlyz/.openclaw/workspace')
from scripts.lib.db_connector import get_db_connection

conn = get_db_connection()
c = conn.cursor()

files = [
    'execution_log.md',
    'result_summary.md',
    'task_summary.md',
    '目标客户清单60家.xlsx',
    '目标客户清单说明文档.md',
    'generate_customer_list.py'
]

for filename in files:
    file_path = f'/Users/mettlyz/.openclaw/workspace/output/task-1718/{filename}'
    file_size = os.path.getsize(file_path)
    file_type = filename.split('.')[-1]
    
    c.execute('''INSERT INTO attachments 
        (entity_type, entity_id, filename, url, size, file_type) 
        VALUES (%s, %s, %s, %s, %s, %s)''',
        ('task', 1718, filename, 
         f'output/task-1718/{filename}', 
         file_size, file_type))
    # print(f'✅ 附件已上传: {filename}')

conn.commit()
conn.close()
# print('所有附件上传完成')
