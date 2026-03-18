#!/usr/bin/env python3
"""
更新日历数据库表结构
"""
import sqlite3
import os

DB_PATH = '/Users/mettlyz/.openclaw/workspace/kanban-react/backend/kanban_v5.db'

def update_calendar_tables():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # 检查calendar_events表的列
    c.execute("PRAGMA table_info(calendar_events)")
    columns = [col[1] for col in c.fetchall()]
    print(f"Current columns: {columns}")
    
    # 添加缺失的列
    new_columns = [
        ('project_id', 'INTEGER'),
        ('task_id', 'INTEGER'),
        ('entity_id', 'INTEGER'),
        ('external_id', 'TEXT'),
        ('external_source', 'TEXT'),
        ('sync_status', 'TEXT'),
        ('last_sync_at', 'DATETIME'),
        ('recurrence', 'TEXT'),
        ('recurrence_end', 'DATETIME'),
        ('is_recurring', 'INTEGER DEFAULT 0'),
        ('parent_event_id', 'INTEGER'),
        ('status', 'TEXT'),
        ('priority', 'INTEGER DEFAULT 0'),
        ('category', 'TEXT'),
        ('event_color', 'TEXT'),
        ('reminder_minutes', 'INTEGER DEFAULT 15'),
        ('participants', 'TEXT'),
        ('meeting_minutes_id', 'TEXT'),
    ]
    
    for col_name, col_type in new_columns:
        if col_name not in columns:
            try:
                c.execute(f"ALTER TABLE calendar_events ADD COLUMN {col_name} {col_type}")
                print(f"Added column: {col_name}")
            except Exception as e:
                print(f"Error adding {col_name}: {e}")
    
    # 创建calendar_accounts表
    c.execute('''
        CREATE TABLE IF NOT EXISTS calendar_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            account_type TEXT NOT NULL,
            server_url TEXT,
            username TEXT,
            password TEXT,
            calendar_path TEXT,
            calendar_name TEXT,
            sync_enabled INTEGER DEFAULT 1,
            last_sync_at DATETIME,
            sync_interval INTEGER DEFAULT 300,
            color TEXT,
            is_default INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    print("Created calendar_accounts table")
    
    # 创建calendar_sync_log表
    c.execute('''
        CREATE TABLE IF NOT EXISTS calendar_sync_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id INTEGER,
            event_id INTEGER,
            action TEXT,
            status TEXT,
            error_message TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    print("Created calendar_sync_log table")
    
    # 创建calendar_attendees表
    c.execute('''
        CREATE TABLE IF NOT EXISTS calendar_attendees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id INTEGER NOT NULL,
            entity_id INTEGER,
            email TEXT,
            name TEXT,
            status TEXT DEFAULT 'needs-action',
            is_organizer INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    print("Created calendar_attendees table")
    
    # 创建calendar_settings表
    c.execute('''
        CREATE TABLE IF NOT EXISTS calendar_settings (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            default_view TEXT DEFAULT 'month',
            first_day_of_week INTEGER DEFAULT 0,
            show_weekends INTEGER DEFAULT 1,
            working_hours_start TEXT DEFAULT '09:00',
            working_hours_end TEXT DEFAULT '18:00',
            default_reminder_minutes INTEGER DEFAULT 15,
            enable_notifications INTEGER DEFAULT 1,
            notification_sound INTEGER DEFAULT 1,
            sync_enabled INTEGER DEFAULT 0,
            sync_interval_minutes INTEGER DEFAULT 30,
            default_calendar_color TEXT DEFAULT '#667eea',
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    print("Created calendar_settings table")
    
    # 插入默认设置
    c.execute("INSERT OR IGNORE INTO calendar_settings (id) VALUES (1)")
    print("Inserted default calendar settings")
    
    conn.commit()
    conn.close()
    print("\nDatabase update completed!")

if __name__ == '__main__':
    update_calendar_tables()
