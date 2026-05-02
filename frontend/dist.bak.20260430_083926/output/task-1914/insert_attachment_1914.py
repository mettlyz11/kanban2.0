#!/usr/bin/env python3
"""
Task #1914 - Attachment Insertion Script
Inserts the patent disclosure document into attachments table
"""
import os
import sys

# Add workspace to path
import os
os.chdir('/Users/mettlyz/.openclaw/workspace')
sys.path.insert(0, '/Users/mettlyz/.openclaw/workspace/scripts')

from lib.db_connector import get_db_connection

def main():
    conn = get_db_connection()
    c = conn.cursor()
    
    file_path = '/Users/mettlyz/.openclaw/workspace/output/task-1914/T109_Hermes_高价值专利技术披露书_20260425.md'
    
    if not os.path.exists(file_path):
        print(f"❌ 文件不存在: {file_path}")
        return 1
    
    file_size = os.path.getsize(file_path)
    filename = os.path.basename(file_path)
    
    # Check if already exists
    c.execute("SELECT id FROM attachments WHERE entity_type = %s AND entity_id = %s AND filename = %s",
              ('task', 1914, filename))
    if c.fetchone():
        print(f"⚠️ 附件已存在，跳过插入: {filename}")
        conn.close()
        return 0
    
    # Insert attachment
    c.execute('''INSERT INTO attachments 
        (entity_type, entity_id, filename, url, size, file_type, created_at) 
        VALUES (%s, %s, %s, %s, %s, %s, NOW())''',
        ('task', 1914, filename, 
         f'output/task-1914/{filename}', 
         file_size, 'md'))
    
    conn.commit()
    conn.close()
    print(f"✅ 附件已上传: {filename} ({file_size} bytes)")
    return 0

if __name__ == '__main__':
    sys.exit(main())
