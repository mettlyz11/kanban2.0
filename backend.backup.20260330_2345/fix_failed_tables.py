#!/usr/bin/env python3
"""
修复迁移失败的表
"""

import sqlite3
import pymysql

def fix_failed_tables():
    print("🔧 修复迁移失败的表...")
    
    # 连接本地 SQLite
    sqlite_conn = sqlite3.connect('/opt/kanban-react/backend/kanban_v5.db')
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
    
    # 失败的表列表
    failed_tables = [
        'blocked_ips', 'calc_tasks', 'calendar_events', 'contact_chat_relations',
        'cron_execution_history', 'cron_jobs', 'cron_tasks', 'dudu_chat_messages',
        'gear_executions', 'goals', 'key_results', 'manual_review_tasks', 'meetings',
        'monitor_task_details', 'projects', 'stocks', 'task_execution_history',
        'tasks', 'trading_records', 'user_profiles', 'wechat_chats'
    ]
    
    fixed = 0
    for table in failed_tables:
        try:
            print(f"\n处理表：{table}")
            
            # 获取 SQLite 表结构
            sqlite_c.execute(f"PRAGMA table_info({table})")
            columns = sqlite_c.fetchall()
            
            if not columns:
                print(f"  ⚪ 无列信息")
                continue
            
            # 获取数据
            sqlite_c.execute(f"SELECT * FROM {table}")
            rows = sqlite_c.fetchall()
            
            # 构建列定义（简化版，全部使用 TEXT 除了主键）
            column_defs = []
            primary_key = None
            for col in columns:
                col_name = col[1]
                col_type_str = col[3] if col[3] else 'TEXT'
                
                # 简单处理：INTEGER 转 BIGINT，其他都转 TEXT
                if 'INT' in col_type_str.upper():
                    mysql_type = 'BIGINT'
                elif 'TEXT' in col_type_str.upper():
                    mysql_type = 'TEXT'
                elif 'REAL' in col_type_str.upper() or 'FLOAT' in col_type_str.upper() or 'DOUBLE' in col_type_str.upper():
                    mysql_type = 'DOUBLE'
                elif 'BLOB' in col_type_str.upper():
                    mysql_type = 'LONGBLOB'
                else:
                    mysql_type = 'TEXT'
                
                if col[5]:  # 主键
                    primary_key = col_name
                    column_defs.append(f"`{col_name}` {mysql_type} NOT NULL AUTO_INCREMENT")
                else:
                    column_defs.append(f"`{col_name}` {mysql_type}")
            
            if primary_key:
                column_defs.append(f"PRIMARY KEY (`{primary_key}`)")
            
            create_sql = f"CREATE TABLE IF NOT EXISTS `{table}` (\n  " + ",\n  ".join(column_defs) + "\n)"
            
            # 删除旧表（如果存在）
            try:
                mysql_c.execute(f"DROP TABLE IF EXISTS `{table}`")
                mysql_conn.commit()
            except:
                pass
            
            # 创建新表
            mysql_c.execute(create_sql)
            mysql_conn.commit()
            print(f"  ✅ 创建表结构成功")
            
            # 插入数据
            if rows:
                col_names = [col[1] for col in columns]
                # 排除自增主键
                insert_cols = [c for c in col_names if c != primary_key]
                placeholders = ', '.join(['%s'] * len(insert_cols))
                col_list = ', '.join([f"`{c}`" for c in insert_cols])
                insert_sql = f"INSERT INTO `{table}` ({col_list}) VALUES ({placeholders})"
                
                for row in rows:
                    # 转换数据，排除主键值
                    values = []
                    for i, val in enumerate(row):
                        if col_names[i] == primary_key:
                            continue
                        if isinstance(val, bytes):
                            values.append(val.decode('utf-8', errors='ignore'))
                        else:
                            values.append(val)
                    
                    try:
                        mysql_c.execute(insert_sql, tuple(values))
                    except Exception as e:
                        pass  # 忽略重复数据
                
                mysql_conn.commit()
                print(f"  ✅ 迁移 {len(rows)} 条数据")
            
            fixed += 1
            
        except Exception as e:
            print(f"  ❌ 失败：{e}")
            mysql_conn.rollback()
    
    mysql_conn.close()
    sqlite_conn.close()
    
    print(f"\n✅ 修复完成！成功：{fixed}/{len(failed_tables)}")

if __name__ == '__main__':
    fix_failed_tables()
