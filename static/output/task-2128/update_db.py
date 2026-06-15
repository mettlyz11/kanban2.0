#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import os
sys.path.insert(0, os.path.expanduser('~/.openclaw/workspace/scripts'))

from lib.db_connector import get_db_connection
import os

# 读取三个摘要文本
with open('/Users/mettlyz/.openclaw/workspace/output/task-2128/任务执行日志_2026-04-27.md', 'r') as f:
    execution_log = f.read()

with open('/Users/mettlyz/.openclaw/workspace/output/task-2128/成果摘要_2026-04-27.md', 'r') as f:
    result_summary = f.read()

with open('/Users/mettlyz/.openclaw/workspace/output/task-2128/任务摘要_2026-04-27.md', 'r') as f:
    task_summary = f.read()

# 更新tasks表
conn = get_db_connection()
c = conn.cursor()

c.execute('''UPDATE tasks 
             SET status = %s, execution_log = %s, result_summary = %s, task_summary = %s, updated_at = NOW() 
             WHERE id = %s''',
          ('completed', execution_log, result_summary, task_summary, 2128))

# print(f"Tasks表已更新，影响行数: {c.rowcount}")

# 插入附件记录
files = [
    ('AI材料赛道_Pre-A轮估值模型_2026-04-27.xlsx', 'xlsx'),
    ('AI材料赛道_Pre-A轮估值模型说明文档_2026-04-27.md', 'md'),
    ('AI材料赛道_投资人关注点深度调研报告_2026-04-27.md', 'md'),
    ('AI材料赛道_融资策略优化方案_2026-04-27.md', 'md'),
    ('任务执行日志_2026-04-27.md', 'md'),
    ('成果摘要_2026-04-27.md', 'md'),
    ('任务摘要_2026-04-27.md', 'md'),
]

for filename, file_type in files:
    filepath = f'/Users/mettlyz/.openclaw/workspace/output/task-2128/{filename}'
    size = os.path.getsize(filepath)
    
    c.execute('''INSERT INTO attachments 
                 (entity_type, entity_id, filename, url, size, file_type, created_at) 
                 VALUES (%s, %s, %s, %s, %s, %s, NOW())''',
              ('task', 2128, filename, f'output/task-2128/{filename}', size, file_type))
    
    # print(f"附件已插入: {filename} ({size} bytes)")

conn.commit()
conn.close()
# print("\n✅ 数据库更新完成！")
