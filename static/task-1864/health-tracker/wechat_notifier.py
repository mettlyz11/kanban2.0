
import os
import sys
sys.path.insert(0, '/Users/mettlyz/.openclaw/workspace/scripts')
from lib.db_connector import get_db_connection

# 连接数据库
conn = get_db_connection()
c = conn.cursor()

# 所有需要插入的文件路径
files = [
    # 根目录文件
    "README.md",
    "execution_log.md",
    "result_summary.md",
    "task_summary.md",
    # code目录
    "code/health_tracker.py",
    "code/influxdb_client.py",
    "code/wechat_notifier.py",
    "code/grafana_dashboard.py",
    "code/generate_dashboard_screenshots.py",
    "code/generate_monthly_report.py",
    # data目录
    "data/health_data.json",
    "data/health_data.csv",
    "data/influxdb_mock.json",
    # docker目录
    "docker/docker-compose.yml",
    # docs目录
    "docs/dashboard_preview.md",
    # grafana目录
    "grafana/health_dashboard.json",
    # reports目录
    "reports/monthly_report.json",
    "reports/monthly_health_report.md",
    "reports/monthly_health_report.html",
    # screenshots目录
    "screenshots/01_score_trend.png",
    "screenshots/02_dimensions_radar.png",
    "screenshots/03_metrics_cards.png",
    "screenshots/04_score_distribution.png",
    "screenshots/05_weekly_heatmap.png",
]

base_dir = "/Users/mettlyz/.openclaw/workspace/output/task-1864/"

# 逐个插入附件
for filename in files:
    file_path = os.path.join(base_dir, filename)
    if os.path.exists(file_path):
        file_size = os.path.getsize(file_path)
        # 确定文件类型
        ext = os.path.splitext(filename)[1].lower()
        file_type = ext[1:] if ext else 'unknown'
        
        c.execute('''INSERT INTO attachments 
            (entity_type, entity_id, filename, url, size, file_type) 
            VALUES (%s, %s, %s, %s, %s, %s)''',
            ('task', 1864, os.path.basename(filename), 
             f'output/task-1864/{filename}', 
             file_size, file_type))
        # print(f'✅ 附件已上传: {filename}')
    else:
        # print(f'⚠️ 文件不存在，跳过: {filename}')

# 读取三个摘要内容
with open(os.path.join(base_dir, 'execution_log.md'), 'r') as f:
    execution_log = f.read()

with open(os.path.join(base_dir, 'result_summary.md'), 'r') as f:
    result_summary = f.read()

with open(os.path.join(base_dir, 'task_summary.md'), 'r') as f:
    task_summary = f.read()

# 更新tasks表
c.execute('UPDATE tasks SET status = %s, execution_log = %s, result_summary = %s, task_summary = %s, updated_at = NOW() WHERE id = %s',
    ('completed', execution_log, result_summary, task_summary, 1864))

conn.commit()
conn.close()
# print('✅ 数据库已更新，任务标记为完成')
