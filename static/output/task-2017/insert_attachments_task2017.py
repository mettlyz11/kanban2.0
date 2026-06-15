#!/usr/bin/env python3
"""
任务#2017附件上传脚本
将报告和Excel文件插入attachments表
"""

import os
import sys

# 添加工作目录到路径
sys.path.insert(0, '/Users/mettlyz/.openclaw/workspace')

try:
    from lib.db_connector import get_db_connection
except ImportError:
    # print("错误：无法导入db_connector")
    sys.exit(1)

def insert_attachment(entity_type, entity_id, filename, file_path, file_type):
    """插入单个附件到数据库"""
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        file_size = os.path.getsize(file_path)
        
        c.execute('''INSERT INTO attachments 
            (entity_type, entity_id, filename, url, size, file_type, created_at) 
            VALUES (%s, %s, %s, %s, %s, %s, NOW())''',
            (entity_type, entity_id, filename, 
             f'output/task-2017/{filename}', 
             file_size, file_type))
        
        conn.commit()
        conn.close()
        # print(f'✅ 附件已上传: {filename} ({file_size} bytes)')
        return True
    except Exception as e:
        # print(f'❌ 上传失败 {filename}: {str(e)}')
        return False

def main():
    # print("开始上传任务#2017的附件...\n")
    
    # 附件1：调研报告
    report_path = '/Users/mettlyz/.openclaw/workspace/output/task-2017/AI4S千万ARR商业模式分析报告_2026-04-26.md'
    insert_attachment('task', 2017, 'AI4S千万ARR商业模式分析报告_2026-04-26.md', report_path, 'md')
    
    # 附件2：数据Excel
    excel_path = '/Users/mettlyz/.openclaw/workspace/output/task-2017/AI4S千万ARR商业模式数据.xlsx'
    if os.path.exists(excel_path):
        insert_attachment('task', 2017, 'AI4S公司对标数据_2026-04-26.xlsx', excel_path, 'xlsx')
    else:
        # 使用其他存在的Excel文件
        excel_path2 = '/Users/mettlyz/.openclaw/workspace/output/task-2017/AI4S商业模式数据汇总_20260426.xlsx'
        if os.path.exists(excel_path2):
            insert_attachment('task', 2017, 'AI4S公司对标数据_2026-04-26.xlsx', excel_path2, 'xlsx')
    
    # print("\n✅ 所有附件上传完成！")

if __name__ == '__main__':
    main()
