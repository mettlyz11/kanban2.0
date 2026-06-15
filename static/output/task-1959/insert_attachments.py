#!/usr/bin/env python3
"""插入任务附件到数据库
"""

import os
import sys

# 添加工作目录到路径
sys.path.insert(0, '/Users/mettlyz/.openclaw/workspace/scripts')

from lib.db_connector import get_db_connection

def insert_attachment(cursor, task_id, filename, file_path, file_type):
    """插入单个附件"""
    try:
        full_path = os.path.join('/Users/mettlyz/.openclaw/workspace', file_path)
        file_size = os.path.getsize(full_path)
        # print(f"插入附件: {filename}, 大小: {file_size} bytes")
        
        cursor.execute('''
            INSERT INTO attachments (entity_type, entity_id, filename, url, size, file_type, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, NOW())
        ''', ('task', task_id, filename, file_path, file_size, file_type))
        return True
    except Exception as e:
        # print(f"插入附件失败 {filename}: {e}")
        return False

def main():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    task_id = 1959
    
    # 核心交付文件列表
    attachments = [
        # (文件名, 文件路径, 文件类型)
        ('AI催化赛道融资项目数据库_20260425.md', 
         'output/task-1959/AI催化赛道融资项目数据库_20260425.md', 'md'),
        ('技术壁垒评估框架与Top10潜力项目_20260425.md',
         'output/task-1959/技术壁垒评估框架与Top10潜力项目_20260425.md', 'md'),
        ('天使轮投资渠道Mapping_20260425.md',
         'output/task-1959/天使轮投资渠道Mapping_20260425.md', 'md'),
    ]
    
    success_count = 0
    for filename, file_path, file_type in attachments:
        if insert_attachment(cursor, task_id, filename, file_path, file_type):
            success_count += 1
    
    conn.commit()
    conn.close()
    
    # print(f"\n✅ 成功插入 {success_count}/{len(attachments)} 个附件到数据库")

if __name__ == '__main__':
    main()
