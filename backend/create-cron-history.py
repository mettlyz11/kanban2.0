
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

# 创建 cron_history 表
create_sql = """
CREATE TABLE IF NOT EXISTS cron_history (
    id BIGINT AUTO_INCREMENT PRIMARY KEY,
    task_id BIGINT NOT NULL,
    task_name VARCHAR(255),
    status VARCHAR(50) NOT NULL,
    output TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_task_id (task_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""

cursor.execute(create_sql)
conn.commit()
print("✅ cron_history 表创建成功")

cursor.execute("DESCRIBE cron_history")
columns = cursor.fetchall()
print("\n=== cron_history 表结构 ===")
for col in columns:
    print(f"  {col['Field']}: {col['Type']}")

# 验证表是否存在
cursor.execute("SHOW TABLES LIKE 'cron_history'")
result = cursor.fetchall()
if result:
    print("\n✅ 验证成功: cron_history 表已存在")
else:
    print("\n❌ 验证失败: cron_history 表不存在")

cursor.close()
conn.close()
