#!/usr/bin/env python3
import pymysql

conn = pymysql.connect(
    host='rm-2zew4su9p966e8x2ofo.mysql.rds.aliyuncs.com',
    user='kanban',
    password='Irc210Irc210!',
    database='kanban'
)

cursor = conn.cursor()

statements = [
    "ALTER TABLE tasks ADD COLUMN slurm_job_id INTEGER NULL",
    "ALTER TABLE tasks ADD COLUMN slurm_output_file TEXT NULL",
    "ALTER TABLE tasks ADD COLUMN retry_count INTEGER DEFAULT 0",
]

for stmt in statements:
    try:
        cursor.execute(stmt)
        print(f'✅ {stmt}')
    except Exception as e:
        if 'Duplicate' in str(e):
            print(f'ℹ️  字段已存在：{stmt}')
        else:
            print(f'❌ 失败：{stmt} - {e}')

conn.commit()
conn.close()
print('\n✅ 数据库迁移完成')
