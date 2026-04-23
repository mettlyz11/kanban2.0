#!/usr/bin/env python3
"""
简化版迁移脚本 - 手动创建表结构并迁移数据
"""

import sqlite3
import pymysql

# RDS 连接
mysql_conn = pymysql.connect(
    host='rm-2zew4su9p966e8x2ofo.mysql.rds.aliyuncs.com',
    port=3306,
    user='kanban',
    password='Irc210Irc210!',
    database='kanban',
    charset='utf8mb4',
    autocommit=False
)
mysql_c = mysql_conn.cursor()

# SQLite 连接
sqlite_conn = sqlite3.connect('/opt/kanban-react/backend/kanban_v5.db')
sqlite_conn.row_factory = sqlite3.Row
sqlite_c = sqlite_conn.cursor()

# 手动定义表结构（MySQL 语法）
create_statements = {
    'meetings': """
        CREATE TABLE IF NOT EXISTS `meetings` (
            `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
            `title` TEXT NOT NULL,
            `date` TEXT,
            `time` TEXT,
            `participants` TEXT,
            `summary` TEXT,
            `content` TEXT,
            `action_items` TEXT,
            `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    
    'tasks': """
        CREATE TABLE IF NOT EXISTS `tasks` (
            `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
            `project_id` BIGINT,
            `title` TEXT NOT NULL,
            `description` TEXT,
            `status` TEXT,
            `priority` TEXT,
            `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            `details` TEXT,
            `start_time` TIMESTAMP NULL,
            `end_time` TIMESTAMP NULL,
            `is_locked` TINYINT(1) DEFAULT 0,
            `lock_time` TIMESTAMP NULL,
            `locked_by` TEXT,
            `locked_at` TIMESTAMP NULL,
            `result_summary` TEXT,
            `depends_on` BIGINT,
            `requires_audit` TINYINT(1) DEFAULT 0,
            `audit_status` TEXT
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    
    'projects': """
        CREATE TABLE IF NOT EXISTS `projects` (
            `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
            `number` TEXT,
            `chinese_name` TEXT,
            `english_name` TEXT,
            `description` TEXT,
            `status` TEXT,
            `priority` TEXT,
            `deadline` DATE,
            `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            `completed_at` TIMESTAMP NULL,
            `failed_at` TIMESTAMP NULL,
            `summary` TEXT,
            `lessons_learned` TEXT,
            `completion_date` TIMESTAMP NULL,
            `name` TEXT,
            `goal` TEXT,
            `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    
    'calendar_events': """
        CREATE TABLE IF NOT EXISTS `calendar_events` (
            `id` TEXT PRIMARY KEY,
            `title` TEXT NOT NULL,
            `description` TEXT,
            `start_time` TIMESTAMP NULL,
            `end_time` TIMESTAMP NULL,
            `location` TEXT,
            `is_all_day` TINYINT(1) DEFAULT 0,
            `project_id` BIGINT,
            `task_id` BIGINT,
            `entity_id` BIGINT,
            `external_id` TEXT,
            `external_source` TEXT,
            `sync_status` TEXT,
            `last_sync_at` DATETIME,
            `recurrence` TEXT,
            `recurrence_end` DATETIME,
            `is_recurring` TINYINT(1) DEFAULT 0,
            `parent_event_id` BIGINT,
            `status` TEXT,
            `priority` BIGINT,
            `category` TEXT,
            `event_color` TEXT,
            `reminder_minutes` BIGINT,
            `participants` TEXT,
            `meeting_minutes_id` TEXT
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """,
    
    'user_profiles': """
        CREATE TABLE IF NOT EXISTS `user_profiles` (
            `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
            `name` TEXT,
            `english_name` TEXT,
            `position` TEXT,
            `company` TEXT,
            `department` TEXT,
            `email` TEXT,
            `phone` TEXT,
            `location` TEXT,
            `bio` TEXT,
            `expertise` TEXT,
            `education` TEXT,
            `awards` TEXT,
            `avatar_url` TEXT,
            `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """
}

def migrate_table(table_name, exclude_pk=False):
    """迁移单个表的数据"""
    print(f"\n迁移表：{table_name}")
    
    try:
        # 创建表
        if table_name in create_statements:
            mysql_c.execute(create_statements[table_name])
            mysql_conn.commit()
            print(f"  ✅ 表结构创建成功")
        
        # 获取 SQLite 数据
        sqlite_c.execute(f"SELECT * FROM {table_name}")
        rows = sqlite_c.fetchall()
        
        if not rows:
            print(f"  ⚪ 无数据")
            return
        
        # 获取列名
        col_names = [desc[0] for desc in sqlite_c.description]
        
        # 排除主键（如果是自增）
        if exclude_pk and 'id' in col_names:
            insert_cols = [c for c in col_names if c != 'id']
        else:
            insert_cols = col_names
        
        placeholders = ', '.join(['%s'] * len(insert_cols))
        col_list = ', '.join([f"`{c}`" for c in insert_cols])
        insert_sql = f"INSERT INTO `{table_name}` ({col_list}) VALUES ({placeholders})"
        
        # 迁移数据
        print(f"  📦 迁移 {len(rows)} 条数据...")
        
        for row in rows:
            # 转换数据
            values = []
            for i, val in enumerate(row):
                col_name = col_names[i]
                
                # 排除自增主键
                if exclude_pk and col_name == 'id':
                    continue
                
                # 处理 bytes
                if isinstance(val, bytes):
                    values.append(val.decode('utf-8', errors='ignore'))
                else:
                    values.append(val)
            
            try:
                mysql_c.execute(insert_sql, tuple(values))
            except Exception as e:
                # 忽略重复键等错误
                pass
        
        mysql_conn.commit()
        print(f"  ✅ 完成")
        
    except Exception as e:
        print(f"  ❌ 错误：{e}")
        mysql_conn.rollback()

# 执行迁移
print("=" * 60)
print("开始迁移关键表到 RDS")
print("=" * 60)

tables_to_migrate = [
    ('meetings', False),
    ('tasks', True),
    ('projects', True),
    ('calendar_events', False),  # id 是 TEXT 类型，不是自增
    ('user_profiles', True),
]

for table, exclude_pk in tables_to_migrate:
    migrate_table(table, exclude_pk)

print("\n" + "=" * 60)
print("迁移完成！")
print("=" * 60)

# 验证
for table, _ in tables_to_migrate:
    try:
        mysql_c.execute(f"SELECT COUNT(*) FROM `{table}`")
        count = mysql_c.fetchone()[0]
        print(f"  {table}: {count} 条记录")
    except:
        print(f"  {table}: 验证失败")

mysql_conn.close()
sqlite_conn.close()
