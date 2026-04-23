
import os
import pymysql
from pymysql.cursors import DictCursor

config = {
    "host": os.environ.get("MYSQL_HOST", "rm-2zew4su9p966e8x2ofo.mysql.rds.aliyuncs.com"),
    "port": int(os.environ.get("MYSQL_PORT", "3306")),
    "user": os.environ.get("MYSQL_USER", "kanban"),
    "password": os.environ.get("MYSQL_PASSWORD", "Irc210Irc210!"),
    "database": os.environ.get("MYSQL_DATABASE", "kanban"),
    "charset": "utf8mb4",
    "cursorclass": DictCursor
}

conn = pymysql.connect(**config)
cursor = conn.cursor()
cursor.execute("SHOW TABLES")
all_tables = cursor.fetchall()
table_names = [list(t.values())[0] for t in all_tables]
cron_tables = [t for t in table_names if "cron" in t.lower()]
print("Cron相关表:", cron_tables)

for table_name in cron_tables:
    print(f"\n=== {table_name} 表结构 ===")
    cursor.execute(f"DESCRIBE {table_name}")
    columns = cursor.fetchall()
    for col in columns:
        print(f"  {col['Field']}: {col['Type']}")

# 检查 cron_history
if "cron_history" in table_names:
    print(f"\n=== cron_history 表结构 ===")
    cursor.execute("DESCRIBE cron_history")
    columns = cursor.fetchall()
    for col in columns:
        print(f"  {col['Field']}: {col['Type']}")
else:
    print("\n❌ cron_history 表不存在!")

# 对比API代码期望的结构
print("\n=== 对比API期望结构 ===")
print("cron_tasks 期望字段: id, name, description, schedule, command, status, last_run, next_run, fail_count, created_at")
print("cron_history 期望字段: id, task_id, task_name, status, output, created_at")

cursor.close()
conn.close()
