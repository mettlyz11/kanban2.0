#!/usr/bin/env python3
"""
任务1953附件上传脚本
上传轨迹记录模块设计文档、失败分类器代码、自改进Prompt模板库
"""

import os
import sys
from lib.db_connector import get_db_connection

def insert_attachment(cursor, task_id, filename, file_path, file_type):
    """插入单个附件"""
    file_size = os.path.getsize(file_path)
    
    cursor.execute("""
        INSERT INTO attachments 
        (entity_type, entity_id, filename, url, size, file_type, created_at) 
        VALUES (%s, %s, %s, %s, %s, %s, NOW())
    """, (
        'task', 
        task_id, 
        filename, 
        f'output/task-1953/{filename}', 
        file_size, 
        file_type
    ))
    
    print(f"✅ 已上传附件: {filename} ({file_size} bytes)")

def main():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    base_path = '/Users/mettlyz/.openclaw/workspace/output/task-1953'
    
    files = [
        ('Agent轨迹记录模块设计文档_2026-04-25.md', 'md'),
        ('failure_classifier.py', 'py'),
        ('自改进Prompt生成模板库_2026-04-25.md', 'md'),
    ]
    
    print("开始上传任务1953附件...")
    
    for filename, file_type in files:
        file_path = os.path.join(base_path, filename)
        if os.path.exists(file_path):
            insert_attachment(cursor, 1953, filename, file_path, file_type)
        else:
            print(f"⚠️ 文件不存在: {file_path}")
    
    conn.commit()
    conn.close()
    
    print("\n✅ 所有附件上传完成!")

if __name__ == "__main__":
    main()
