#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
插入附件记录到数据库
任务ID: 2122
"""

import sys
import os
sys.path.insert(0, '/Users/mettlyz/.openclaw/workspace/scripts')

import pymysql
from lib.db_connector import get_db_connection

def get_file_size(filepath):
    """获取文件大小（字节）"""
    try:
        return os.path.getsize(filepath)
    except:
        return 0

def main():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 附件列表
    attachments = [
        {
            'filename': '2026北京小升初政保政策汇编_20260426.md',
            'url': 'output/task-2122/2026北京小升初政保政策汇编_20260426.md',
            'filepath': '/Users/mettlyz/.openclaw/workspace/output/task-2122/2026北京小升初政保政策汇编_20260426.md',
            'file_type': 'md'
        },
        {
            'filename': '政保成功案例分析与关键要素总结_20260426.md',
            'url': 'output/task-2122/政保成功案例分析与关键要素总结_20260426.md',
            'filepath': '/Users/mettlyz/.openclaw/workspace/output/task-2122/政保成功案例分析与关键要素总结_20260426.md',
            'file_type': 'md'
        },
        {
            'filename': '小升初三条升学路径设计与时间规划_20260426.md',
            'url': 'output/task-2122/小升初三条升学路径设计与时间规划_20260426.md',
            'filepath': '/Users/mettlyz/.openclaw/workspace/output/task-2122/小升初三条升学路径设计与时间规划_20260426.md',
            'file_type': 'md'
        },
        {
            'filename': '政保申请材料清单与准备指南_20260426.md',
            'url': 'output/task-2122/政保申请材料清单与准备指南_20260426.md',
            'filepath': '/Users/mettlyz/.openclaw/workspace/output/task-2122/政保申请材料清单与准备指南_20260426.md',
            'file_type': 'md'
        }
    ]
    
    try:
        for att in attachments:
            size = get_file_size(att['filepath'])
            # print(f"插入附件: {att['filename']}, 大小: {size} bytes")
            
            cursor.execute('''
                INSERT INTO attachments 
                (entity_type, entity_id, filename, url, size, file_type, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, NOW())
            ''', (
                'task',
                2122,
                att['filename'],
                att['url'],
                size,
                att['file_type']
            ))
        
        conn.commit()
        # print(f"\n成功插入 {len(attachments)} 条附件记录")
        
    except Exception as e:
        # print(f"插入附件失败: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    main()
