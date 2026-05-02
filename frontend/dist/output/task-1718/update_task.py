import sys
sys.path.append('/Users/mettlyz/.openclaw/workspace')
from scripts.lib.db_connector import get_db_connection

# 读取各个日志文件
with open('execution_log.md', 'r') as f:
    execution_log = f.read()

with open('result_summary.md', 'r') as f:
    result_summary = f.read()

with open('task_summary.md', 'r') as f:
    task_summary = f.read()

# 更新数据库
conn = get_db_connection()
c = conn.cursor()
c.execute('UPDATE tasks SET status = %s, execution_log = %s, result_summary = %s, task_summary = %s, updated_at = NOW() WHERE id = %s',
    ('completed', execution_log, result_summary, task_summary, 1718))
conn.commit()
affected_rows = c.rowcount
conn.close()

print(f'✅ 数据库已更新，影响行数: {affected_rows}')
print(f'✅ 任务 #1718 已标记为 completed')
