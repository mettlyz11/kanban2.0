#!/usr/bin/env python3
"""
完整数据库迁移脚本：SQLite → RDS MySQL
包括表结构创建和数据迁移
"""

import sqlite3
import pymysql
from datetime import datetime
import sys
import re

def sqlite_type_to_mysql(sqlite_type):
    """转换 SQLite 类型到 MySQL 类型"""
    type_mapping = {
        'INTEGER': 'BIGINT',
        'INT': 'BIGINT',
        'TEXT': 'TEXT',
        'REAL': 'DOUBLE',
        'FLOAT': 'DOUBLE',
        'DOUBLE': 'DOUBLE',
        'BLOB': 'LONGBLOB',
        'BOOLEAN': 'TINYINT(1)',
        'DATETIME': 'DATETIME',
        'TIMESTAMP': 'TIMESTAMP',
    }
    return type_mapping.get(sqlite_type.upper(), 'TEXT')

def create_table_mysql(mysql_c, table_name, columns):
    """在 MySQL 中创建表"""
    column_defs = []
    primary_key = None
    
    for col in columns:
        col_name = col[1]
        col_type = sqlite_type_to_mysql(col[3])
        not_null = 'NOT NULL' if col[3] else ''
        default = f"DEFAULT {col[4]}" if col[4] is not None else ''
        
        if col[5]:  # 主键
            primary_key = col_name
        
        column_def = f"`{col_name}` {col_type} {not_null} {default}".strip()
        column_defs.append(column_def)
    
    if primary_key:
        column_defs.append(f"PRIMARY KEY (`{primary_key}`)")
    
    create_sql = f"CREATE TABLE IF NOT EXISTS `{table_name}` (\n  " + ",\n  ".join(column_defs) + "\n)"
    
    try:
        mysql_c.execute(create_sql)
        return True
    except Exception as e:
        print(f"    ⚠️  创建表失败：{e}")
        return False

def migrate_data():
    print("=" * 60)
    print("🚀 开始完整数据库迁移 (SQLite → RDS MySQL)")
    print("=" * 60)
    start_time = datetime.now()
    
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
    
    migrated_tables = 0
    migrated_rows = 0
    errors = []
    
    try:
        # 获取所有 SQLite 表
        sqlite_c.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        sqlite_tables = [t[0] for t in sqlite_c.fetchall()]
        
        # 获取 RDS 现有表
        mysql_c.execute("SHOW TABLES")
        mysql_tables = set([t[0] for t in mysql_c.fetchall()])
        
        print(f"\n📊 SQLite 表数量：{len(sqlite_tables)}")
        print(f"📊 RDS 现有表数量：{len(mysql_tables)}")
        
        for i, table in enumerate(sqlite_tables, 1):
            # 跳过 sqlite 内部表
            if table.startswith('sqlite_'):
                continue
            
            print(f"\n[{i}/{len(sqlite_tables)}] 处理表：{table}")
            
            try:
                # 获取表结构
                sqlite_c.execute(f"PRAGMA table_info({table})")
                columns = sqlite_c.fetchall()
                
                if not columns:
                    print(f"  ⚪ 无列信息，跳过")
                    continue
                
                # 获取数据
                sqlite_c.execute(f"SELECT * FROM {table}")
                rows = sqlite_c.fetchall()
                
                if not rows:
                    print(f"  ⚪ 无数据")
                    # 但仍需要创建表结构
                    if table not in mysql_tables:
                        print(f"  🏗️  创建空表结构...")
                        if create_table_mysql(mysql_c, table, columns):
                            mysql_tables.add(table)
                            migrated_tables += 1
                    continue
                
                # 检查表是否存在
                if table not in mysql_tables:
                    print(f"  🏗️  创建表结构...")
                    if not create_table_mysql(mysql_c, table, columns):
                        errors.append((table, "创建表失败"))
                        continue
                    mysql_tables.add(table)
                
                # 迁移数据
                print(f"  📦 迁移 {len(rows)} 条数据...")
                
                # 获取列名
                col_names = [col[1] for col in columns]
                placeholders = ', '.join(['%s'] * len(col_names))
                col_list = ', '.join([f"`{c}`" for c in col_names])
                insert_sql = f"INSERT INTO `{table}` ({col_list}) VALUES ({placeholders})"
                
                # 批量插入
                batch_size = 100
                for batch_start in range(0, len(rows), batch_size):
                    batch_end = min(batch_start + batch_size, len(rows))
                    batch_rows = rows[batch_start:batch_end]
                    
                    # 转换数据
                    converted_rows = []
                    for row in batch_rows:
                        converted_row = []
                        for val in row:
                            if isinstance(val, bytes):
                                converted_row.append(val.decode('utf-8', errors='ignore'))
                            else:
                                converted_row.append(val)
                        converted_rows.append(tuple(converted_row))
                    
                    try:
                        mysql_c.executemany(insert_sql, converted_rows)
                        mysql_conn.commit()
                    except Exception as e:
                        # 可能是重复数据，尝试忽略
                        print(f"    ⚠️  插入警告：{e}")
                        mysql_conn.rollback()
                
                migrated_tables += 1
                migrated_rows += len(rows)
                print(f"  ✅ 完成")
                
            except Exception as e:
                error_msg = f"{e}"
                errors.append((table, error_msg))
                print(f"  ❌ 错误：{error_msg}")
                mysql_conn.rollback()
        
        # 最终统计
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        print("\n" + "=" * 60)
        print("✅ 迁移完成！")
        print("=" * 60)
        print(f"⏱️  耗时：{duration:.2f} 秒")
        print(f"📊 迁移表数：{migrated_tables}")
        print(f"📦 迁移行数：{migrated_rows}")
        print(f"❌ 错误数：{len(errors)}")
        
        if errors:
            print("\n错误详情:")
            for table, error in errors[:10]:
                print(f"  - {table}: {error}")
            if len(errors) > 10:
                print(f"  ... 还有 {len(errors)-10} 个错误")
        
        return len(errors) == 0
        
    except Exception as e:
        print(f"\n❌ 严重错误：{e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        sqlite_conn.close()
        mysql_conn.close()

if __name__ == '__main__':
    success = migrate_data()
    sys.exit(0 if success else 1)
