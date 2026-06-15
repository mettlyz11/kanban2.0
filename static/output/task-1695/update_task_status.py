#!/usr/bin/env python3
"""
更新任务#1695状态为completed
"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../scripts'))

from lib.db_connector import get_db_connection, execute_update

def read_file(file_path):
    """读取文件内容"""
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.read()

def main():
    # 任务ID
    task_id = 1695
    
    # 读取执行日志、结果总结、任务总结
    workspace_root = '/Users/mettlyz/.openclaw/workspace'
    execution_log_path = os.path.join(workspace_root, 'output/task-1695/execution_log.md')
    result_summary_path = os.path.join(workspace_root, 'output/task-1695/result_summary.md')
    task_summary_path = os.path.join(workspace_root, 'output/task-1695/task_summary.md')
    
    try:
        execution_log_text = read_file(execution_log_path)
        result_summary_text = read_file(result_summary_path)
        task_summary_text = read_file(task_summary_path)
    except Exception as e:
        # print(f'❌ 读取文件失败: {e}')
        return 1
    
    # 验证长度要求
    if len(execution_log_text) < 200:
        # print(f'❌ execution_log 长度不足: {len(execution_log_text)} 字符 (<200)')
        return 1
    
    if len(result_summary_text) < 50:
        # print(f'❌ result_summary 长度不足: {len(result_summary_text)} 字符 (<50)')
        return 1
    
    if len(task_summary_text) < 50 or len(task_summary_text) > 100:
        # print(f'⚠️  task_summary 长度: {len(task_summary_text)} 字符 (建议50-100)')
        # 不强制失败，仅警告
    
    # print(f'📊 文件长度验证通过:')
    # print(f'   execution_log: {len(execution_log_text)} 字符')
    # print(f'   result_summary: {len(result_summary_text)} 字符')
    # print(f'   task_summary: {len(task_summary_text)} 字符')
    
    # 更新数据库
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        sql = '''UPDATE tasks SET status = %s, execution_log = %s, 
                 result_summary = %s, task_summary = %s, updated_at = NOW() 
                 WHERE id = %s'''
        
        params = ('completed', execution_log_text, result_summary_text, 
                  task_summary_text, task_id)
        
        c.execute(sql, params)
        conn.commit()
        
        affected_rows = c.rowcount
        conn.close()
        
        if affected_rows == 1:
            # print(f'✅ 数据库已更新: 任务 #{task_id} 状态设置为 completed')
            return 0
        else:
            # print(f'❌ 更新失败: 未找到任务 #{task_id}')
            return 1
            
    except Exception as e:
        # print(f'❌ 数据库更新失败: {e}')
        return 1

if __name__ == '__main__':
    sys.exit(main())