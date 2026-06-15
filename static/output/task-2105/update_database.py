#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
看板任务 #2105 数据库更新脚本
"""

import sys
sys.path.insert(0, '/Users/mettlyz/.openclaw/workspace')

from lib.db_connector import get_db_connection, execute_query, execute_update

def main():
    # 读取文件内容
    with open('/Users/mettlyz/.openclaw/workspace/output/task-2105/execution_log_task2105.md', 'r', encoding='utf-8') as f:
        execution_log = f.read()
    
    with open('/Users/mettlyz/.openclaw/workspace/output/task-2105/result_summary_task2105.md', 'r', encoding='utf-8') as f:
        result_summary = f.read()
    
    with open('/Users/mettlyz/.openclaw/workspace/output/task-2105/task_summary_task2105.md', 'r', encoding='utf-8') as f:
        task_summary = f.read()
    
    # 更新任务状态
    update_sql = """
    UPDATE tasks 
    SET status = %s, 
        execution_log = %s, 
        result_summary = %s, 
        task_summary = %s, 
        updated_at = NOW() 
    WHERE id = %s
    """
    
    params = ('completed', execution_log, result_summary, task_summary, 2105)
    
    try:
        affected_rows = execute_update(update_sql, params)
        # print(f"✅ 任务 #2105 状态已更新为 completed，影响行数: {affected_rows}")
    except Exception as e:
        # print(f"❌ 更新任务状态失败: {e}")
        return False
    
    # 插入附件记录
    attachments = [
        ('task', 2105, '和光智成_Pre-A轮融资_Executive_Summary_20260426.md', 'output/task-2105/和光智成_Pre-A轮融资_Executive_Summary_20260426.md', 2200, 'md'),
        ('task', 2105, '和光智成_Pre-A轮融资_Teaser_20260426.md', 'output/task-2105/和光智成_Pre-A轮融资_Teaser_20260426.md', 4700, 'md'),
        ('task', 2105, '和光智成_Pre-A轮融资_BP_完整版_20260426.md', 'output/task-2105/和光智成_Pre-A轮融资_BP_完整版_20260426.md', 15000, 'md'),
        ('task', 2105, '和光智成_Pre-A轮融资_30家目标投资人清单_20260426.md', 'output/task-2105/和光智成_Pre-A轮融资_30家目标投资人清单_20260426.md', 4700, 'md'),
    ]
    
    insert_sql = """
    INSERT INTO attachments (entity_type, entity_id, filename, url, size, file_type, created_at)
    VALUES (%s, %s, %s, %s, %s, %s, NOW())
    """
    
    for attachment in attachments:
        try:
            params_with_time = attachment + ()  # NOW() is handled in SQL
            affected_rows = execute_update(insert_sql, attachment)
            # print(f"✅ 附件已插入: {attachment[2]}")
        except Exception as e:
            # print(f"⚠️  附件插入可能重复或出错 {attachment[2]}: {e}")
    
    # print("\n🎉 数据库更新完成！")
    return True

if __name__ == '__main__':
    main()
