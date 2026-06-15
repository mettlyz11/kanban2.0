import sys
sys.path.insert(0, '/Users/mettlyz/.openclaw/workspace/scripts/lib')
import os
from db_connector import get_db_connection

conn = get_db_connection()
c = conn.cursor()

file_list = [
    '任务#1973_执行日志_20260425.md',
    '任务#1973_结果摘要_20260425.md',
    '双一流对标分析_完整报告_20260425.md',
    '双一流建设对标分析与提升路径建议报告_20260425.md',
    '双一流建设政策与对标数据搜索摘要_20260425.md',
    '双一流政策与化学学科发展研究报告_子代理搜索成果_20260425.md',
    '双一流建设对标分析与提升路径建议_报告_20260425.md'
]

base_dir = '/Users/mettlyz/.openclaw/workspace/output/task-1973/'

for filename in file_list:
    file_path = os.path.join(base_dir, filename)
    if os.path.exists(file_path):
        file_size = os.path.getsize(file_path)
        c.execute('''INSERT INTO attachments 
            (entity_type, entity_id, filename, url, size, file_type) 
            VALUES (%s, %s, %s, %s, %s, %s)''',
            ('task', 1973, filename, 
             f'output/task-1973/{filename}', 
             file_size, 'md'))
        # print(f'✅ 附件已上传: {filename} ({file_size} bytes)')
    else:
        # print(f'❌ 文件不存在: {filename}')

conn.commit()
conn.close()
# print('所有附件插入完成')
