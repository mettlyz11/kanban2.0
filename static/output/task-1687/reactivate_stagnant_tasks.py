#!/usr/bin/env python3
"""
重新激活停滞任务
"""

import sys
sys.path.insert(0, 'scripts')
from lib.db_connector import get_db_connection
from datetime import datetime

def reactivate_tasks():
    conn = get_db_connection()
    c = conn.cursor()
    
    # 获取停滞任务
    query = """
        SELECT id, title, status, updated_at, spawn_attempt, spawn_error, notes
        FROM tasks 
        WHERE status IN ('in_progress', 'pending') 
        AND updated_at < DATE_SUB(NOW(), INTERVAL 24 HOUR)
        ORDER BY updated_at ASC
    """
    c.execute(query)
    tasks = c.fetchall()
    
    # print(f"找到 {len(tasks)} 个停滞任务")
    
    reactivated = []
    skipped = []
    
    for task in tasks:
        task_id = task['id']
        title = task['title']
        current_status = task['status']
        spawn_attempt = task['spawn_attempt'] or 0
        spawn_error = task['spawn_error']
        notes = task['notes'] or ''
        
        # 决定操作：重新激活
        # 更新 updated_at 为当前时间，添加注释，重置 spawn_attempt 和 spawn_error
        new_notes = notes + f"\n[重新激活 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 任务停滞超过24小时，已重新激活以供调度器拾取。"
        
        update_query = """
            UPDATE tasks 
            SET updated_at = NOW(),
                notes = %s,
                spawn_attempt = 0,
                spawn_error = NULL,
                subagent_session_key = NULL
            WHERE id = %s
        """
        try:
            c.execute(update_query, (new_notes, task_id))
            reactivated.append(task_id)
            # print(f"✅ 重新激活任务 {task_id}: {title}")
        except Exception as e:
            # print(f"❌ 更新任务 {task_id} 失败: {e}")
            skipped.append(task_id)
    
    conn.commit()
    
    # 验证更新
    c.execute("SELECT COUNT(*) as count FROM tasks WHERE id IN %s AND updated_at >= DATE_SUB(NOW(), INTERVAL 5 MINUTE)", (tuple(reactivated),))
    updated_count = c.fetchone()['count']
    
    # print(f"\n=== 重新激活完成 ===")
    # print(f"总停滞任务: {len(tasks)}")
    # print(f"成功重新激活: {len(reactivated)}")
    # print(f"跳过: {len(skipped)}")
    # print(f"验证更新: {updated_count} 个任务更新时间已刷新")
    
    # 获取更新后的任务状态
    c.execute("SELECT id, title, status, updated_at FROM tasks WHERE id IN %s", (tuple(reactivated),))
    updated_tasks = c.fetchall()
    
    conn.close()
    
    return {
        'total_stagnant': len(tasks),
        'reactivated': reactivated,
        'skipped': skipped,
        'updated_tasks': updated_tasks
    }

if __name__ == "__main__":
    result = reactivate_tasks()
    # 保存结果到文件
    import json
    output_path = "/Users/mettlyz/.openclaw/workspace/output/task-1687/reactivation_result.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2, default=str)
    # print(f"\n结果已保存到: {output_path}")