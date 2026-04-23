#!/usr/bin/env python3
import database_config
from database_config import get_db_connection

with get_db_connection() as conn:
    c = conn.cursor()
    c.execute('DESCRIBE projects')
    columns = c.fetchall()
    print('projects表结构:')
    for col in columns:
        print(f'  {col["Field"]}: {col["Type"]}')

    print('\n查询项目ID 42, 44, 46, 50:')
    for pid in [42, 44, 46, 50]:
        c.execute('SELECT * FROM projects WHERE id = %s', (pid,))
        result = c.fetchone()
        if result:
            print(f'项目 {pid}: 存在 - ID={result["id"]}, 名称={result.get("name", result.get("title", "N/A"))}, 状态={result.get("status", "N/A")}')
        else:
            print(f'项目 {pid}: 不存在')
