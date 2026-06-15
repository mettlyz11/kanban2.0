#!/usr/bin/env python3
"""
查询停滞任务（超过24小时无更新）
"""

import sys
sys.path.insert(0, 'scripts')
from lib.db_connector import get_db_connection
from datetime import datetime, timedelta

def main():
    conn = get_db_connection()
    c = conn.cursor()
    
    # 查询超过24小时无更新的任务（状态为in_progress或pending）
    query = """
        SELECT id, title, status, updated_at, created_at, execution_log, result_summary 
        FROM tasks 
        WHERE status IN ('in_progress', 'pending') 
        AND updated_at < DATE_SUB(NOW(), INTERVAL 24 HOUR)
        ORDER BY updated_at ASC
        LIMIT 30
    """
    c.execute(query)
    tasks = c.fetchall()
    
    # print(f"Found {len(tasks)} stagnant tasks:")
    for task in tasks:
        task_id = task['id']
        title = task['title']
        status = task['status']
        updated_at = task['updated_at']
        created_at = task['created_at']
        exec_log = task['execution_log']
        result_sum = task['result_summary']
        log_len = len(exec_log) if exec_log else 0
        sum_len = len(result_sum) if result_sum else 0
        # print(f"ID: {task_id}, Title: {title}, Status: {status}, Updated: {updated_at}")
        # print(f"  Log length: {log_len}, Summary length: {sum_len}")
        # 检查是否满足完成条件
        if log_len >= 200 and sum_len >= 50:
            # print(f"  ✅ 满足完成条件 (log≥200, summary≥50)")
        else:
            # print(f"  ❌ 不满足完成条件 (log={log_len}, summary={sum_len})")
        # print()
    
    conn.close()
    
    # 输出摘要
    # print("\n=== 摘要 ===")
    # print(f"总停滞任务数: {len(tasks)}")
    if len(tasks) > 0:
        # 按状态分组
        status_counts = {}
        for task in tasks:
            status = task['status']
            status_counts[status] = status_counts.get(status, 0) + 1
        for status, count in status_counts.items():
            # print(f"状态 '{status}': {count} 个任务")
    
    return tasks

if __name__ == "__main__":
    main()