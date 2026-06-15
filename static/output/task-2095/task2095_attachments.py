# -*- coding: utf-8 -*-
import sys
sys.path.insert(0, '/Users/mettlyz/.openclaw/workspace/scripts')
from pathlib import Path
from lib.db_connector import get_db_connection

files = [
    ('硅研新材诉讼_证据链评估与补充建议报告_2026-04-26.md', 'output/task-2095/硅研新材诉讼_证据链评估与补充建议报告_2026-04-26.md', 'md'),
    ('硅研新材诉讼_证据清单_2026-04-26.csv', 'output/task-2095/硅研新材诉讼_证据清单_2026-04-26.csv', 'csv'),
]

conn = get_db_connection()
c = conn.cursor()
for filename, url, ftype in files:
    size = Path('/Users/mettlyz/.openclaw/workspace', url).stat().st_size
    c.execute("SELECT COUNT(*) AS cnt FROM attachments WHERE entity_type=%s AND entity_id=%s AND filename=%s AND url=%s", ('task', 2095, filename, url))
    row = c.fetchone()
    cnt = row['cnt'] if isinstance(row, dict) else row[0]
    if cnt == 0:
        c.execute('''INSERT INTO attachments (entity_type, entity_id, filename, url, size, file_type) VALUES (%s,%s,%s,%s,%s,%s)''', ('task', 2095, filename, url, size, ftype))
        # print('inserted', filename, size)
    else:
        # print('exists', filename, size)
conn.commit()
conn.close()
# print('attachments done')
