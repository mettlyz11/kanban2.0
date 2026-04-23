#!/usr/bin/env python3
"""
修复 calendar_events 表
"""

import pymysql
import sqlite3

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
sqlite_c = sqlite_conn.cursor()

print("修复 calendar_events 表...")

try:
    # 删除旧表
    mysql_c.execute("DROP TABLE IF EXISTS `calendar_events`")
    
    # 创建新表（id 使用 VARCHAR 而不是 TEXT）
    mysql_c.execute("""
        CREATE TABLE `calendar_events` (
            `id` VARCHAR(255) PRIMARY KEY,
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
    """)
    mysql_conn.commit()
    print("✅ 表结构创建成功")
    
    # 迁移数据
    sqlite_c.execute("SELECT * FROM calendar_events")
    rows = sqlite_c.fetchall()
    
    if rows:
        col_names = [desc[0] for desc in sqlite_c.description]
        placeholders = ', '.join(['%s'] * len(col_names))
        col_list = ', '.join([f"`{c}`" for c in col_names])
        insert_sql = f"INSERT INTO `calendar_events` ({col_list}) VALUES ({placeholders})"
        
        print(f"📦 迁移 {len(rows)} 条数据...")
        
        for row in rows:
            values = []
            for val in row:
                if isinstance(val, bytes):
                    values.append(val.decode('utf-8', errors='ignore'))
                else:
                    values.append(val)
            
            try:
                mysql_c.execute(insert_sql, tuple(values))
            except Exception as e:
                pass
        
        mysql_conn.commit()
        print("✅ 数据迁移完成")
    
    # 验证
    mysql_c.execute("SELECT COUNT(*) FROM `calendar_events`")
    count = mysql_c.fetchone()[0]
    print(f"✅ 验证：{count} 条记录")
    
except Exception as e:
    print(f"❌ 错误：{e}")
    mysql_conn.rollback()

finally:
    mysql_conn.close()
    sqlite_conn.close()
