#!/usr/bin/env python3
"""更新看板任务#1035状态并上传附件"""

import subprocess
import sys

db_host = "rm-2zew4su9p966e8x2ofo.mysql.rds.aliyuncs.com"
db_user = "kanban"
db_password = "Irc210Irc210!"
db_name = "kanban"
ssh_key = "/Users/mettlyz/.openclaw/workspace/info/aliserver1.pem"
ssh_host = "root@47.93.184.128"
attachment_base = "/opt/kanban-react/backend/attachments"

def run_sql(sql):
    """执行SQL命令"""
    cmd = f'ssh -i {ssh_key} -o StrictHostKeyChecking=no {ssh_host} "mysql -h {db_host} -u {db_user} -p{db_password} {db_name} -e \\"{sql}\\" 2>&1"'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout + result.stderr

def upload_file(task_id, local_path, remote_filename):
    """上传附件"""
    remote_dir = f"{attachment_base}/task{task_id}"
    remote_path = f"{remote_dir}/{remote_filename}"
    
    # 创建目录
    mkdir_cmd = f"ssh -i {ssh_key} -o StrictHostKeyChecking=no {ssh_host} 'mkdir -p {remote_dir}'"
    subprocess.run(mkdir_cmd, shell=True, capture_output=True)
    
    # 上传文件
    scp_cmd = f"scp -i {ssh_key} -o StrictHostKeyChecking=no {local_path} {ssh_host}:{remote_path}"
    result = subprocess.run(scp_cmd, shell=True, capture_output=True, text=True)
    
    if result.returncode == 0:
        return remote_path
    else:
        return f"ERROR: {result.stderr}"

# 任务ID
task_id = 1035

# 1. 更新任务状态为completed
print("=== 步骤1: 更新任务状态 ===")
summary = "完成七大目标战略复盘与Next-Phase规划报告，涵盖T1-T7全面数据穿透分析、达成度评估、问题识别、90天冲刺计划。核心结论：整体完成度68%，T4财富管理体系100%落地，4/18北航实验室揭牌达成，7月A轮融资为Next-Phase首要目标。"

log_entry = f"""
=== 执行完成 [2026-04-18 22:35] ===
状态: completed

【核心成果摘要】
{summary}

【详细执行日志】
1. 获取看板系统数据：1066个任务全面分析
2. 七大目标数据穿透：T1(75%), T2(55%), T3(40%), T4(95%), T5(85%), T6(55%), T7(70%)
3. 问题识别：pending任务308个待清理，催化剂实验待启动
4. Next-Phase规划：90天冲刺计划，聚焦A轮融资
5. 报告生成：完整战略复盘报告7386字

【关键数据】
- 总任务数: 1,066
- 完成率: 62.9%
- 平均目标完成度: 68%
- T4财富体系: 100%完成
- 北航实验室: 4/18揭牌完成

【附件列表】
1. task1035-strategic-review-report.md - 战略复盘主报告
"""

sql = f"""UPDATE tasks SET 
    status='completed',
    task_summary='{summary[:500]}',
    execution_log=CONCAT(COALESCE(execution_log,''), '{log_entry}'),
    updated_at=NOW()
    WHERE id={task_id};"""

result = run_sql(sql)
print(result)

# 2. 上传附件
print("\n=== 步骤2: 上传附件 ===")
report_path = "/Users/mettlyz/.openclaw/workspace/output/task1035-strategic-review-report.md"
upload_result = upload_file(task_id, report_path, "strategic-review-report.md")
print(f"附件上传结果: {upload_result}")

# 3. 验证更新
print("\n=== 步骤3: 验证更新 ===")
sql_verify = f"SELECT id, status, task_summary FROM tasks WHERE id={task_id};"
result_verify = run_sql(sql_verify)
print(result_verify)

print("\n=== 任务#1035更新完成 ===")
