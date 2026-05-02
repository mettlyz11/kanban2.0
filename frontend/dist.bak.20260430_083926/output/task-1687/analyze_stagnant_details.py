#!/usr/bin/env python3
"""
分析停滞任务的详细信息
"""

import sys
sys.path.insert(0, 'scripts')
from lib.db_connector import get_db_connection

def main():
    conn = get_db_connection()
    c = conn.cursor()
    
    # 查询超过24小时无更新的任务（状态为in_progress或pending）
    query = """
        SELECT id, title, status, updated_at, created_at, execution_log, result_summary,
               description, spawn_error, subagent_session_key, spawn_attempt, retry_count,
               notes, tags, due_date
        FROM tasks 
        WHERE status IN ('in_progress', 'pending') 
        AND updated_at < DATE_SUB(NOW(), INTERVAL 24 HOUR)
        ORDER BY updated_at ASC
        LIMIT 30
    """
    c.execute(query)
    tasks = c.fetchall()
    
    print(f"Found {len(tasks)} stagnant tasks:\n")
    
    for task in tasks:
        print(f"=== ID: {task['id']} ===")
        print(f"标题: {task['title']}")
        print(f"状态: {task['status']}")
        print(f"创建时间: {task['created_at']}")
        print(f"更新时间: {task['updated_at']}")
        print(f"重试次数: {task['retry_count']}")
        print(f"spawn尝试: {task['spawn_attempt']}")
        print(f"子代理会话: {task['subagent_session_key']}")
        print(f"spawn错误: {task['spawn_error'][:100] if task['spawn_error'] else '无'}")
        print(f"标签: {task['tags']}")
        print(f"截止日期: {task['due_date']}")
        print(f"描述长度: {len(task['description']) if task['description'] else 0}")
        print(f"日志长度: {len(task['execution_log']) if task['execution_log'] else 0}")
        print(f"摘要长度: {len(task['result_summary']) if task['result_summary'] else 0}")
        print()
    
    conn.close()
    
    # 分析统计
    print("\n=== 统计分析 ===")
    total = len(tasks)
    with_spawn_error = sum(1 for t in tasks if t['spawn_error'])
    with_subagent = sum(1 for t in tasks if t['subagent_session_key'])
    high_retry = sum(1 for t in tasks if t['retry_count'] > 0)
    print(f"总停滞任务: {total}")
    print(f"有spawn错误的任务: {with_spawn_error}")
    print(f"有子代理会话的任务: {with_subagent}")
    print(f"重试次数>0的任务: {high_retry}")
    
    return tasks

if __name__ == "__main__":
    main()