#!/usr/bin/env python3
import pymysql

# 读取执行日志
with open('/Users/mettlyz/.openclaw/workspace/output/task-1250/execution_log.md', 'r', encoding='utf-8') as f:
    execution_log = f.read()

# 读取结果摘要
with open('/Users/mettlyz/.openclaw/workspace/output/task-1250/result_summary.md', 'r', encoding='utf-8') as f:
    result_summary = f.read()

# 读取任务摘要
with open('/Users/mettlyz/.openclaw/workspace/output/task-1250/task_summary.md', 'r', encoding='utf-8') as f:
    task_summary = f.read()

# 连接数据库
conn = pymysql.connect(
    host='rm-2zew4su9p966e8x2ofo.mysql.rds.aliyuncs.com',
    user='kanban',
    password='Irc210Irc210!',
    database='kanban',
    charset='utf8mb4'
)

c = conn.cursor()

# 更新任务状态
c.execute(
    'UPDATE tasks SET status = %s, execution_log = %s, result_summary = %s, task_summary = %s, updated_at = NOW() WHERE id = %s',
    ('completed', execution_log, result_summary, task_summary, 1250)
)

print(f"更新任务1250状态为completed")
print(f"执行日志长度: {len(execution_log)} 字符")
print(f"结果摘要长度: {len(result_summary)} 字符")
print(f"任务摘要长度: {len(task_summary)} 字符")

# 插入附件记录
files_to_insert = [
    ('task', 1250, 'email_intelligent_monitor.py', 'output/task-1250/email_intelligent_monitor.py', 30000, 'py'),
    ('task', 1250, 'email_analysis_report.json', 'output/task-1250/email_analysis_report.json', 8000, 'json'),
    ('task', 1250, 'email_analysis_report.md', 'output/task-1250/email_analysis_report.md', 12000, 'md'),
    ('task', 1250, 'execution_log.md', 'output/task-1250/execution_log.md', 8000, 'md'),
    ('task', 1250, 'result_summary.md', 'output/task-1250/result_summary.md', 1000, 'md'),
    ('task', 1250, 'task_summary.md', 'output/task-1250/task_summary.md', 200, 'md'),
    ('task', 1250, 'contacts_db.json', 'output/task-1250/contacts_db.json', 1000, 'json'),
]

for entity_type, entity_id, filename, url, size, file_type in files_to_insert:
    try:
        c.execute(
            '''INSERT INTO attachments (entity_type, entity_id, filename, url, size, file_type) 
               VALUES (%s, %s, %s, %s, %s, %s)''',
            (entity_type, entity_id, filename, url, size, file_type)
        )
        print(f"插入附件: {filename}")
    except Exception as e:
        print(f"插入附件 {filename} 失败: {e}")

conn.commit()
conn.close()

print("\n数据库更新完成！")
