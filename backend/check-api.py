#!/usr/bin/env python3
import database_config
from database_config import get_db_connection

# 检查API路由，看看WHERE条件
with get_db_connection() as conn:
    c = conn.cursor()
    # 检查项目42/44/46/50
    for pid in [42, 44, 46, 50]:
        c.execute('SELECT id, name, status FROM projects WHERE id = %s', (pid,))
        result = c.fetchone()
        if result:
            print(f'项目 {pid}: id={result["id"]}, name={result["name"]}, status={result["status"]}')
        else:
            print(f'项目 {pid}: 不存在')
