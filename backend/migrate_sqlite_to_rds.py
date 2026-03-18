#!/usr/bin/env python3
"""
数据库迁移脚本：SQLite → RDS MySQL
"""

import sqlite3
import pymysql
from datetime import datetime
import sys

def migrate_database():
    print("=" * 60)
    print("🚀 开始数据库迁移 (SQLite → RDS MySQL)")
    print("=" * 60)
    
    # 连接本地 SQLite
    sqlite_path = '/opt/kanban-react/backend/kanban_v5.db'
    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_c = sqlite_conn.cursor()
    
    # 连接 RDS MySQL
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
    
    try:
        # 获取所有 SQLite 表
        sqlite_c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        sqlite_tables = [t[0] for t in sqlite_c.fetchall()]
        
        print(f"\n📊 SQLite 表数量：{len(sqlite_tables)}")
        
        # 获取 RDS 现有表
        mysql_c.execute("SHOW TABLES")
        mysql_tables = [t[0] for t in mysql_c.fetchall()]
        print(f"📊 RDS 现有表数量：{len(mysql_tables)}")
        
        # 备份 RDS 现有数据
        print("\n💾 RDS 现有数据状态...")
        backup_tables = []
        for table in mysql_tables:
            try:
                mysql_c.execute(f"SELECT COUNT(*) FROM `{table}`")
                count = mysql_c.fetchone()[0]
                if count > 0:
                    backup_tables.append((table, count))
            except:
                pass
        
        print(f"✅ RDS 有 {len(backup_tables)} 个表包含数据")
        
        # 统计需要迁移的数据
        print("\n📈 数据量统计:")
        total_rows = 0
        for table in sqlite_tables:
            if table.startswith('sqlite_'):
                continue
            sqlite_c.execute(f"SELECT COUNT(*) FROM {table}")
            count = sqlite_c.fetchone()[0]
            if count > 0:
                total_rows += count
                print(f"  {table}: {count} 条")
        
        print(f"\n总计：{total_rows} 条记录需要迁移")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 错误：{e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        sqlite_conn.close()
        mysql_conn.close()

if __name__ == '__main__':
    success = migrate_database()
    sys.exit(0 if success else 1)
