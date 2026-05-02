#!/usr/bin/env python3
import sys
sys.path.insert(0, '/Users/mettlyz/.openclaw/workspace/scripts/lib')
from db_connector import execute_query

# 查看表结构
result = execute_query("DESCRIBE tasks")
print("tasks表结构:")
for col in result:
    print(f"  {col['Field']} - {col['Type']} - {col['Null']} - {col['Key']}")

# 查看最近10条任务
print("\n最近10条任务:")
tasks = execute_query("SELECT id, title, status, created_at FROM tasks ORDER BY id DESC LIMIT 10")
for task in tasks:
    print(f"  [{task['id']}] {task['title']} - {task['status']} - {task['created_at']}")
