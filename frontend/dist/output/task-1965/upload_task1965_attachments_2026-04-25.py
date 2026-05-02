#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
sys.path.insert(0, '/Users/mettlyz/.openclaw/workspace/scripts')
from lib.db_connector import get_db_connection

TASK_ID = 1965
BASE = '/Users/mettlyz/.openclaw/workspace/output/task-1965'
FILES = [
    'OpenClaw调度系统Agentic_Workflow优化方案_2026-04-25.md',
    'OpenClaw调度系统性能对比测试报告_2026-04-25.md',
    'execution_log_2026-04-25.md',
    'openclaw_agentic_scheduler_prototype_2026-04-25.py',
    'benchmark_agentic_scheduler_2026-04-25.py',
]

conn = get_db_connection()
c = conn.cursor()
for name in FILES:
    file_path = os.path.join(BASE, name)
    size = os.path.getsize(file_path)
    ext = name.split('.')[-1]
    c.execute('''INSERT INTO attachments (entity_type, entity_id, filename, url, size, file_type) VALUES (%s, %s, %s, %s, %s, %s)''',
              ('task', TASK_ID, name, f'output/task-1965/{name}', size, ext))
    print(f'✅ 附件已上传: {name}')
conn.commit()
conn.close()
print('done')
