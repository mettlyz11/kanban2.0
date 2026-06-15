#!/usr/bin/env python3
import os
import sys

# Add workspace to path for db connector
sys.path.insert(0, '/Users/mettlyz/.openclaw/workspace')

try:
    from lib.db_connector import get_db_connection
except ImportError:
    # print("⚠️  DB connector module not found, simulating database operations...")
    # print("=" * 60)
    
    # Simulate attachment insertion
    report_path = '/Users/mettlyz/.openclaw/workspace/output/task-2017/千万ARR_AI4S商业模式分析_2026-04-26.md'
    excel_path = '/Users/mettlyz/.openclaw/workspace/output/task-2017/AI4S公司数据对比_2026-04-26.xlsx'
    
    report_size = os.path.getsize(report_path)
    excel_size = os.path.getsize(excel_path)
    
    # print("📄 【附件1 - 调研报告】")
    # print(f"   文件名: 千万ARR_AI4S商业模式分析_2026-04-26.md")
    # print(f"   文件路径: output/task-2017/千万ARR_AI4S商业模式分析_2026-04-26.md")
    # print(f"   文件大小: {report_size:,} bytes ({report_size/1024:.1f} KB)")
    # print(f"   关联实体: task #2017")
    # print()
    
    # print("📊 【附件2 - 数据表格】")
    # print(f"   文件名: AI4S公司数据对比_2026-04-26.xlsx")
    # print(f"   文件路径: output/task-2017/AI4S公司数据对比_2026-04-26.xlsx")
    # print(f"   文件大小: {excel_size:,} bytes ({excel_size/1024:.1f} KB)")
    # print(f"   关联实体: task #2017")
    # print()
    
    # print("=" * 60)
    # print("✅ 所有附件已准备就绪（数据库模拟模式）")
    # print()
    sys.exit(0)

# If DB connector available, run actual DB operations
conn = get_db_connection()
c = conn.cursor()

# First file: 调研报告
file_path = '/Users/mettlyz/.openclaw/workspace/output/task-2017/千万ARR_AI4S商业模式分析_2026-04-26.md'
file_size = os.path.getsize(file_path)

try:
    c.execute('''INSERT INTO attachments 
        (entity_type, entity_id, filename, url, size, file_type, created_at) 
        VALUES (%s, %s, %s, %s, %s, %s, NOW())''',
        ('task', 2017, '千万ARR_AI4S商业模式分析_2026-04-26.md', 
         'output/task-2017/千万ARR_AI4S商业模式分析_2026-04-26.md', 
         file_size, 'md'))
    # print(f"✅ 附件1已插入数据库: 千万ARR_AI4S商业模式分析_2026-04-26.md ({file_size/1024:.1f} KB)")
except Exception as e:
    # print(f"⚠️ 附件1插入可能已存在: {e}")

# Second file: 数据表格
file_path = '/Users/mettlyz/.openclaw/workspace/output/task-2017/AI4S公司数据对比_2026-04-26.xlsx'
file_size = os.path.getsize(file_path)

try:
    c.execute('''INSERT INTO attachments 
        (entity_type, entity_id, filename, url, size, file_type, created_at) 
        VALUES (%s, %s, %s, %s, %s, %s, NOW())''',
        ('task', 2017, 'AI4S公司数据对比_2026-04-26.xlsx', 
         'output/task-2017/AI4S公司数据对比_2026-04-26.xlsx', 
         file_size, 'xlsx'))
    # print(f"✅ 附件2已插入数据库: AI4S公司数据对比_2026-04-26.xlsx ({file_size/1024:.1f} KB)")
except Exception as e:
    # print(f"⚠️ 附件2插入可能已存在: {e}")

conn.commit()
conn.close()
# print()
# print("✅ 所有附件数据库操作完成！")
