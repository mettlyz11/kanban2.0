#!/usr/bin/env python3
"""
更新任务 #1570 状态为 completed 并插入附件
"""

import sys
import os
sys.path.insert(0, '/Users/mettlyz/.openclaw/workspace/scripts')
from lib.db_connector import get_db_connection, execute_update

def read_file(filepath):
    with open(filepath, 'r') as f:
        return f.read()

def main():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    task_id = 1570
    
    # 读取文件内容
    output_dir = '/Users/mettlyz/.openclaw/workspace/output/task-1570'
    
    execution_log = read_file(f'{output_dir}/execution_log_final.md')
    result_summary = read_file(f'{output_dir}/result_summary_final.md')
    task_summary = read_file(f'{output_dir}/task_summary_final.md')
    
    # 更新任务状态
    cursor.execute("""
        UPDATE tasks 
        SET status = 'completed',
            task_summary = %s,
            result_summary = %s,
            execution_log = CONCAT(COALESCE(execution_log, ''), %s),
            updated_at = NOW()
        WHERE id = %s
    """, (task_summary, result_summary, execution_log, task_id))
    
    print(f"✅ 任务 #{task_id} 状态已更新为 completed")
    
    # 要插入的附件列表
    attachments = [
        # 核心报告
        'SDS_DEPLOYMENT_REPORT.md',
        'sds-dashboard.html',
        'sds-status-report.md',
        'sds-safety-report.md',
        'execution_log_final.md',
        'result_summary_final.md',
        'task_summary_final.md',
        
        # 核心代码模块
        'task_analyzer.py',
        'auto_task_generator.py',
        'subagent_scheduler.py',
        'monitoring_72h.py',
        'observability_dashboard.py',
        'safety_guardrails.py',
        'sds_main.py',
        'README.md',
    ]
    
    inserted_count = 0
    
    for filename in attachments:
        # 确定文件路径
        if filename.endswith('.py') or filename == 'README.md':
            filepath = f'/Users/mettlyz/.openclaw/workspace/sds/{filename}'
        else:
            filepath = f'{output_dir}/{filename}'
        
        if not os.path.exists(filepath):
            print(f"⚠️  文件不存在: {filepath}")
            continue
        
        file_size = os.path.getsize(filepath)
        
        # 检查是否已存在
        cursor.execute("""
            SELECT id FROM attachments 
            WHERE entity_type = 'task' AND entity_id = %s AND filename = %s
        """, (task_id, filename))
        
        if cursor.fetchone():
            print(f"⚠️  附件已存在，跳过: {filename}")
            continue
        
        # 插入附件
        cursor.execute("""
            INSERT INTO attachments 
            (entity_type, entity_id, filename, url, size, file_type, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
        """, (
            'task',
            task_id,
            filename,
            f'output/task-1570/{filename}',
            file_size,
            filename.split('.')[-1]
        ))
        
        inserted_count += 1
        print(f"✅ 已插入附件: {filename} ({file_size} bytes)")
    
    conn.commit()
    conn.close()
    
    print(f"\n📊 完成统计:")
    print(f"   - 任务状态已更新: completed")
    print(f"   - 新插入附件数: {inserted_count}")
    print(f"\n🎉 任务 #1570 完成!")

if __name__ == '__main__':
    main()
