#!/usr/bin/env python3
"""
更新任务#1606状态并插入附件
"""
import os
import sys
import pymysql
from lib.db_connector import get_db_connection

# 添加脚本目录到路径，以便导入lib模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../scripts'))

def read_file(filepath):
    """读取文件内容"""
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read()

def main():
    # 文件路径
    base_dir = os.path.dirname(__file__)
    pricing_file = os.path.join(base_dir, 'DFT_platform_pricing_2026-04-22.md')
    poc_file = os.path.join(base_dir, 'POC_template_2026-04-22.md')
    presentation_file = os.path.join(base_dir, 'Client_presentation_outline_2026-04-22.md')
    execution_log_file = os.path.join(base_dir, 'execution_log.md')
    result_summary_file = os.path.join(base_dir, 'result_summary.md')
    task_summary_file = os.path.join(base_dir, 'task_summary.md')
    
    # 读取内容
    execution_log_text = read_file(execution_log_file)
    result_summary_text = read_file(result_summary_file)
    task_summary_text = read_file(task_summary_file)
    
    # 获取文件大小
    def get_file_size(filepath):
        return os.path.getsize(filepath)
    
    # 连接数据库
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # 1. 更新任务状态
        print("更新任务#1606状态...")
        cursor.execute('''
            UPDATE tasks 
            SET status = %s, 
                execution_log = %s, 
                result_summary = %s, 
                task_summary = %s, 
                updated_at = NOW() 
            WHERE id = %s
        ''', ('completed', execution_log_text, result_summary_text, task_summary_text, 1606))
        
        # 2. 插入附件记录
        print("插入附件记录...")
        attachments = [
            ('DFT_platform_pricing_2026-04-22.md', pricing_file, 'md'),
            ('POC_template_2026-04-22.md', poc_file, 'md'),
            ('Client_presentation_outline_2026-04-22.md', presentation_file, 'md')
        ]
        
        for filename, filepath, file_type in attachments:
            if os.path.exists(filepath):
                size = get_file_size(filepath)
                # 构建URL路径（相对于workspace）
                url = f'output/task-1606/{filename}'
                cursor.execute('''
                    INSERT INTO attachments 
                    (entity_type, entity_id, filename, url, size, file_type) 
                    VALUES (%s, %s, %s, %s, %s, %s)
                ''', ('task', 1606, filename, url, size, file_type))
                print(f"  已插入: {filename}")
            else:
                print(f"  警告: 文件不存在 {filepath}")
        
        # 提交事务
        conn.commit()
        print("数据库更新完成！")
        
    except Exception as e:
        conn.rollback()
        print(f"错误: {e}")
        sys.exit(1)
    finally:
        cursor.close()
        conn.close()

if __name__ == '__main__':
    main()