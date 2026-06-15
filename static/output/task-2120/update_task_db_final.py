#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Task #2120 数据库更新脚本
更新任务状态为completed，并插入附件记录
"""

import pymysql
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv(os.path.expanduser('~/.openclaw/.env'))

# 数据库连接配置
DB_CONFIG = {
    'host': 'rm-2zew4su9p966e8x2ofo.mysql.rds.aliyuncs.com',
    'user': 'kanban',
    'password': os.getenv('DB_PASSWORD', ''),
    'database': 'kanban',
    'charset': 'utf8mb4'
}

TASK_ID = 2120

def read_file_content(filepath):
    """读取文件内容"""
    full_path = f'/Users/mettlyz/.openclaw/workspace/output/task-2120/{filepath}'
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        # print(f"读取文件失败 {filepath}: {e}")
        return ""

def get_file_size(filepath):
    """获取文件大小"""
    full_path = f'/Users/mettlyz/.openclaw/workspace/output/task-2120/{filepath}'
    try:
        return os.path.getsize(full_path)
    except Exception as e:
        # print(f"获取文件大小失败 {filepath}: {e}")
        return 0

def update_task_status():
    """更新任务状态为completed"""
    # 读取文本内容
    execution_log = read_file_content('execution_log_20260427.md')
    result_summary = read_file_content('result_summary_20260427.md')
    task_summary = read_file_content('task_summary_20260427.md')
    
    # print(f"execution_log 长度: {len(execution_log)} 字符")
    # print(f"result_summary 长度: {len(result_summary)} 字符")
    # print(f"task_summary 长度: {len(task_summary)} 字符")
    
    try:
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        sql = """
        UPDATE tasks 
        SET status = %s, 
            execution_log = %s, 
            result_summary = %s, 
            task_summary = %s, 
            updated_at = NOW() 
        WHERE id = %s
        """
        
        cursor.execute(sql, ('completed', execution_log, result_summary, task_summary, TASK_ID))
        conn.commit()
        # print(f"✅ 任务 {TASK_ID} 状态已更新为 completed")
        return True
        
    except Exception as e:
        # print(f"❌ 更新任务状态失败: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

def insert_attachments():
    """插入附件记录"""
    attachments = [
        ('AI半导体材料概念股2026年Q2财报前瞻与持仓优化报告.md', 'output/task-2120/AI半导体材料概念股2026年Q2财报前瞻与持仓优化报告.md', 'md'),
        ('多因子评级矩阵_20260427.md', 'output/task-2120/多因子评级矩阵_20260427.md', 'md'),
        ('Q2持仓优化建议书_20260427.md', 'output/task-2120/Q2持仓优化建议书_20260427.md', 'md'),
        ('个股买入卖出时机建议_20260426.md', 'output/task-2120/个股买入卖出时机建议_20260426.md', 'md'),
    ]
    
    try:
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # 先检查是否已存在
        cursor.execute("SELECT COUNT(*) FROM attachments WHERE entity_type = %s AND entity_id = %s", ('task', TASK_ID))
        existing_count = cursor.fetchone()[0]
        # print(f"已存在附件数量: {existing_count}")
        
        inserted_count = 0
        for filename, url, file_type in attachments:
            file_size = get_file_size(filename)
            
            # 检查是否已存在
            cursor.execute("""
                SELECT id FROM attachments 
                WHERE entity_type = %s AND entity_id = %s AND filename = %s
            """, ('task', TASK_ID, filename))
            
            if cursor.fetchone():
                # print(f"⏭️  附件已存在，跳过: {filename}")
                continue
            
            sql = """
            INSERT INTO attachments (entity_type, entity_id, filename, url, size, file_type)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            
            cursor.execute(sql, ('task', TASK_ID, filename, url, file_size, file_type))
            inserted_count += 1
            # print(f"✅ 插入附件: {filename} ({file_size} bytes)")
        
        conn.commit()
        # print(f"✅ 共插入 {inserted_count} 个附件记录")
        return True
        
    except Exception as e:
        # print(f"❌ 插入附件失败: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

def main():
    # print("=" * 60)
    # print("Task #2120 数据库更新")
    # print("=" * 60)
    
    # 检查数据库密码
    if not DB_CONFIG['password']:
        # print("⚠️  警告: 未找到DB_PASSWORD环境变量")
        # print("请确保 ~/.openclaw/.env 文件中包含 DB_PASSWORD=xxx")
        return
    
    # print(f"数据库主机: {DB_CONFIG['host']}")
    # print(f"数据库用户: {DB_CONFIG['user']}")
    # print()
    
    # 更新任务状态
    # print("1. 更新任务状态...")
    update_success = update_task_status()
    # print()
    
    # 插入附件
    # print("2. 插入附件记录...")
    attach_success = insert_attachments()
    # print()
    
    # print("=" * 60)
    if update_success and attach_success:
        # print("✅ 数据库更新全部完成！")
    else:
        # print("⚠️  部分操作可能未完成，请检查错误信息")
    # print("=" * 60)

if __name__ == '__main__':
    main()
