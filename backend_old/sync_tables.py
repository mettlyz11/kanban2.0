#!/usr/bin/env python3
"""
数据库表结构同步脚本
确保服务器数据库拥有完整的表结构
"""
import sqlite3
import sys

def sync_database(db_path):
    """同步数据库表结构"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print(f"=== 同步数据库: {db_path} ===\n")
    
    # 1. 创建日历相关表
    print("1. 检查日历相关表...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS calendar_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            account_type TEXT DEFAULT 'caldav',
            server_url TEXT,
            username TEXT,
            password TEXT,
            calendar_name TEXT,
            sync_enabled INTEGER DEFAULT 1,
            last_sync_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    print("   ✅ calendar_accounts")
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS calendar_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER DEFAULT 1,
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
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    print("   ✅ calendar_settings")
    
    # 2. 创建会议相关表
    print("\n2. 检查会议相关表...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS meeting_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            meeting_date DATE,
            meeting_time TIME,
            location TEXT,
            participants TEXT,
            agenda TEXT,
            content TEXT,
            conclusion TEXT,
            project_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    print("   ✅ meeting_notes")
    
    # 3. 创建调研笔记表
    print("\n3. 检查调研笔记表...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS research_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT,
            category TEXT,
            tags TEXT,
            attachments TEXT,
            ref_links TEXT,
            project_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    print("   ✅ research_notes")
    
    # 4. 创建每日复盘表
    print("\n4. 检查每日复盘表...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            review_date DATE UNIQUE,
            mood TEXT,
            completed TEXT,
            problems TEXT,
            tomorrow_plan TEXT,
            summary TEXT,
            tags TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    print("   ✅ daily_reviews")
    
    # 5. 创建个人信息表
    print("\n5. 检查个人信息表...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS personal_info (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            title TEXT,
            email TEXT,
            phone TEXT,
            location TEXT,
            bio TEXT,
            avatar TEXT,
            skills TEXT,
            education TEXT,
            experience TEXT,
            certifications TEXT,
            social_links TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    print("   ✅ personal_info")
    
    # 6. 创建技能表
    print("\n6. 检查技能表...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS skills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT,
            level INTEGER DEFAULT 1,
            progress INTEGER DEFAULT 0,
            description TEXT,
            resources TEXT,
            certificates TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    print("   ✅ skills")
    
    # 7. 创建版本日志表
    print("\n7. 检查版本日志表...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS version_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            version TEXT NOT NULL,
            release_date DATE,
            changes TEXT,
            type TEXT DEFAULT 'feature',
            author TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    print("   ✅ version_logs")
    
    # 8. 创建资源表
    print("\n8. 检查资源表...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS resources (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type TEXT,
            url TEXT,
            description TEXT,
            category TEXT,
            tags TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    print("   ✅ resources")
    
    # 9. 创建公司信息表
    print("\n9. 检查公司信息表...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS company_info (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            description TEXT,
            industry TEXT,
            founded_date DATE,
            address TEXT,
            contact_email TEXT,
            contact_phone TEXT,
            logo_url TEXT,
            website TEXT,
            team_members TEXT,
            news_updates TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    print("   ✅ company_info")
    
    conn.commit()
    conn.close()
    
    print("\n=== ✅ 所有表结构同步完成 ===")

if __name__ == '__main__':
    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    else:
        db_path = '/opt/kanban-react/backend/kanban_v5.db'
    
    sync_database(db_path)
