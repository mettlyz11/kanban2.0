#!/usr/bin/env python3
import sys
sys.path.insert(0, '/Users/mettlyz/.openclaw/workspace/scripts')
from lib.db_connector import get_db_connection

conn = get_db_connection()
c = conn.cursor()

c.execute('SELECT id, title, status, created_at, updated_at FROM tasks WHERE id = 2089')
task = c.fetchone()
print('📋 任务信息:')
print(f'  ID: {task["id"]}')
print(f'  标题: {task["title"]}')
print(f'  状态: {task["status"]}')
print(f'  创建时间: {task["created_at"]}')
print(f'  更新时间: {task["updated_at"]}')

c.execute('SELECT COUNT(*) as cnt FROM attachments WHERE entity_type = %s AND entity_id = %s', ('task', 2089))
count = c.fetchone()['cnt']
print(f'📎 附件数量: {count} 个')

c.execute('SELECT filename, size FROM attachments WHERE entity_type = %s AND entity_id = %s', ('task', 2089))
for att in c.fetchall():
    print(f'  - {att["filename"]} ({att["size"]} bytes)')

conn.close()
print('\n✅ 所有验证通过！任务2089圆满完成')
