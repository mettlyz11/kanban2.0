import os
import sys
sys.path.insert(0, '/Users/mettlyz/.openclaw/workspace/scripts')
from lib.db_connector import get_db_connection

conn = get_db_connection()
c = conn.cursor()

files = [
    ('化工行业数字化转型需求分析报告_20260426.md', '报告'),
    ('Top20潜在客户优先级评分表_20260426.md', '表格'),
    ('化工企业客户切入策略与试点项目建议_20260426.md', '策略方案')
]

for filename, desc in files:
    file_path = f'/Users/mettlyz/.openclaw/workspace/output/task-2089/{filename}'
    file_size = os.path.getsize(file_path)
    
    c.execute('''INSERT INTO attachments 
        (entity_type, entity_id, filename, url, size, file_type, description) 
        VALUES (%s, %s, %s, %s, %s, %s, %s)''',
        ('task', 2089, filename, 
         f'output/task-2089/{filename}', 
         file_size, 'md', desc))
    print(f'✅ 附件已上传: {filename} ({file_size} bytes)')

conn.commit()
conn.close()
print('\n🎉 所有附件上传完成！')
