import os
from lib.db_connector import get_db_connection

# 连接数据库
conn = get_db_connection()
c = conn.cursor()

# 1. 插入附件到attachments表
files = [
    "无感健康设备对比评估报告_调研分析_20260426.md",
    "个人健康监测体系架构设计_架构方案_20260426.md",
    "2026年度高管健康管理全方案_管理方案_20260426.md",
    "健康投入效能提升量化测算模型_测算模型_20260426.md"
]

base_dir = "/Users/mettlyz/.openclaw/workspace/output/task-1998/"

for filename in files:
    file_path = os.path.join(base_dir, filename)
    file_size = os.path.getsize(file_path)
    c.execute('''INSERT INTO attachments 
        (entity_type, entity_id, filename, url, size, file_type) 
        VALUES (%s, %s, %s, %s, %s, %s)''',
        ('task', 1998, filename, 
         f'output/task-1998/{filename}', 
         file_size, 'md'))
    print(f'✅ 附件已上传: {filename} ({file_size}字节)')

# 2. 读取执行日志、结果摘要、任务摘要
with open(os.path.join(base_dir, 'execution_log.md'), 'r', encoding='utf-8') as f:
    execution_log = f.read()

with open(os.path.join(base_dir, 'result_summary.md'), 'r', encoding='utf-8') as f:
    result_summary = f.read()

with open(os.path.join(base_dir, 'task_summary.md'), 'r', encoding='utf-8') as f:
    task_summary = f.read()

# 3. 更新tasks表
c.execute('UPDATE tasks SET status = %s, execution_log = %s, result_summary = %s, task_summary = %s, updated_at = NOW() WHERE id = %s',
    ('completed', execution_log, result_summary, task_summary, 1998))

conn.commit()
conn.close()
print('✅ 数据库tasks表已更新，任务标记为completed')
print('🎉 任务#1998全部流程完成！')
