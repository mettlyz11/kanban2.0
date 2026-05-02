import os
from lib.db_connector import get_db_connection

# 数据库连接
conn = get_db_connection()
c = conn.cursor()

# 第一步：插入所有附件到attachments表
output_dir = '/Users/mettlyz/.openclaw/workspace/output/task-1959/'
attachment_files = [
    'AI催化赛道一级市场调研_任务摘要_2026-04-25.md',
    'AI催化赛道一级市场调研_执行日志_2026-04-25.md',
    'AI催化赛道一级市场调研_结果摘要_2026-04-25.md',
    'AI催化赛道天使投资渠道Mapping_报告_2026-04-25.md',
    'AI催化赛道融资项目数据库_2026-04-25.md',
    '技术壁垒评估框架与Top10潜力项目_20260425.md',
    '天使轮投资渠道Mapping_FA天使联盟社群_20260425.md',
    '任务完成确认报告_2026-04-25.md'
]

for filename in attachment_files:
    file_path = os.path.join(output_dir, filename)
    if os.path.exists(file_path):
        file_size = os.path.getsize(file_path)
        c.execute('''INSERT INTO attachments 
            (entity_type, entity_id, filename, url, size, file_type) 
            VALUES (%s, %s, %s, %s, %s, %s)''',
            ('task', 1959, filename, 
             f'output/task-1959/{filename}', 
             file_size, 'md'))
        print(f'✅ 附件已上传: {filename} (大小: {file_size}字节)')
    else:
        print(f'⚠️ 文件不存在: {filename}')

conn.commit()
print(f'\n✅ 共成功上传 {len(attachment_files)} 个附件到数据库')

# 第二步：读取三个核心内容字段
with open(os.path.join(output_dir, 'AI催化赛道一级市场调研_执行日志_2026-04-25.md'), 'r', encoding='utf-8') as f:
    execution_log = f.read()

with open(os.path.join(output_dir, 'AI催化赛道一级市场调研_结果摘要_2026-04-25.md'), 'r', encoding='utf-8') as f:
    result_summary = f.read()

with open(os.path.join(output_dir, 'AI催化赛道一级市场调研_任务摘要_2026-04-25.md'), 'r', encoding='utf-8') as f:
    task_summary = f.read()

# 第三步：更新tasks表
c.execute('UPDATE tasks SET status = %s, execution_log = %s, result_summary = %s, task_summary = %s, updated_at = NOW() WHERE id = %s',
    ('completed', execution_log, result_summary, task_summary, 1959))
conn.commit()
print(f'\n✅ 任务#1959 状态已更新为 completed')
print(f'   - execution_log 长度: {len(execution_log)} 字符')
print(f'   - result_summary 长度: {len(result_summary)} 字符')
print(f'   - task_summary 长度: {len(task_summary)} 字符')

# 验证更新结果
c.execute('SELECT status, LENGTH(execution_log), LENGTH(result_summary), LENGTH(task_summary) FROM tasks WHERE id = 1959')
result = c.fetchone()
print(f'\n✅ 数据库验证结果:')
print(f'   - 状态: {result[0]}')
print(f'   - execution_log 长度: {result[1]} 字符 (要求≥200)')
print(f'   - result_summary 长度: {result[2]} 字符 (要求≥50)')
print(f'   - task_summary 长度: {result[3]} 字符 (要求50-100+)')

conn.close()
print('\n🎉 任务#1959 所有处理流程已完成！')
