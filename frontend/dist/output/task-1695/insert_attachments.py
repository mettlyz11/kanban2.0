#!/usr/bin/env python3
"""
插入任务#1695的附件到数据库
"""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../scripts'))

from lib.db_connector import get_db_connection

def insert_attachment(entity_type, entity_id, filename, url, size, file_type):
    """插入单个附件到数据库"""
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute('''INSERT INTO attachments 
            (entity_type, entity_id, filename, url, size, file_type) 
            VALUES (%s, %s, %s, %s, %s, %s)''',
            (entity_type, entity_id, filename, url, size, file_type))
        conn.commit()
        print(f'✅ 附件已上传: {filename} (大小: {size} 字节)')
        return True
    except Exception as e:
        print(f'❌ 插入附件失败: {filename}, 错误: {e}')
        conn.rollback()
        return False
    finally:
        conn.close()

def main():
    # 任务ID
    task_id = 1695
    entity_type = 'task'
    
    # 附件列表
    attachments = [
        {
            'filename': '系统记忆更新与知识库维护报告_20260423.md',
            'url': 'output/task-1695/系统记忆更新与知识库维护报告_20260423.md',
            'file_type': 'md'
        },
        {
            'filename': 'execution_log.md',
            'url': 'output/task-1695/execution_log.md',
            'file_type': 'md'
        },
        {
            'filename': 'result_summary.md',
            'url': 'output/task-1695/result_summary.md',
            'file_type': 'md'
        },
        {
            'filename': 'task_summary.md',
            'url': 'output/task-1695/task_summary.md',
            'file_type': 'md'
        }
    ]
    
    # 工作空间根目录
    workspace_root = '/Users/mettlyz/.openclaw/workspace'
    
    # 插入每个附件
    success_count = 0
    for att in attachments:
        file_path = os.path.join(workspace_root, att['url'])
        if not os.path.exists(file_path):
            print(f'❌ 文件不存在: {file_path}')
            continue
        
        file_size = os.path.getsize(file_path)
        if insert_attachment(entity_type, task_id, att['filename'], att['url'], file_size, att['file_type']):
            success_count += 1
    
    print(f'\n📊 附件上传完成: {success_count}/{len(attachments)} 个文件成功上传')
    
    if success_count == len(attachments):
        print('✅ 所有附件上传成功')
        return 0
    else:
        print('⚠️  部分附件上传失败')
        return 1

if __name__ == '__main__':
    sys.exit(main())