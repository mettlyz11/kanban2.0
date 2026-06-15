import os
from lib.db_connector import get_db_connection

conn = get_db_connection()
c = conn.cursor()

output_dir = '/Users/mettlyz/.openclaw/workspace/output/task-1952'
files = [
    'DeepSeekR1_材料科学计算Benchmark_20260425.md',
    'DeepSeekR1_GPT4.1_材料科学数学推理对比报告_20260425.md',
    '分子式计算Agent原型_20260425.py',
    'execution_log.md',
    'result_summary.md',
    'task_summary.md'
]

for filename in files:
    file_path = os.path.join(output_dir, filename)
    file_size = os.path.getsize(file_path)
    file_type = 'py' if filename.endswith('.py') else 'md'
    
    c.execute('''INSERT INTO attachments 
        (entity_type, entity_id, filename, url, size, file_type) 
        VALUES (%s, %s, %s, %s, %s, %s)''',
        ('task', 1952, filename, 
         f'output/task-1952/{filename}', 
         file_size, file_type))
    # print(f'✅ 附件已上传: {filename} ({file_size} bytes)')

conn.commit()
conn.close()
# print('🎉 所有附件上传完成！')
