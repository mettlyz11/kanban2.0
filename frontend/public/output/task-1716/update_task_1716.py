#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
任务1716 数据库更新脚本
功能：1. 插入4个产出文件到attachments表 2. 更新tasks表状态为completed
"""

import os
import pymysql
from lib.db_connector import get_db_connection

# 文件列表
files = [
    {
        "filename": "和光智成_产品定价策略与商业模式设计方案_20260423.md",
        "path": "/Users/mettlyz/.openclaw/workspace/output/task-1716/和光智成_产品定价策略与商业模式设计方案_20260423.md",
        "file_type": "md",
        "description": "主方案：产品定价策略与商业模式设计完整方案"
    },
    {
        "filename": "任务1716_执行日志.md",
        "path": "/Users/mettlyz/.openclaw/workspace/output/task-1716/任务1716_执行日志.md",
        "file_type": "md",
        "description": "执行日志：详细记录执行过程、使用工具、问题解决方案"
    },
    {
        "filename": "任务1716_结果摘要.md",
        "path": "/Users/mettlyz/.openclaw/workspace/output/task-1716/任务1716_结果摘要.md",
        "file_type": "md",
        "description": "结果摘要：总结核心成果与关键发现"
    },
    {
        "filename": "任务1716_任务摘要.md",
        "path": "/Users/mettlyz/.openclaw/workspace/output/task-1716/任务1716_任务摘要.md",
        "file_type": "md",
        "description": "任务摘要：50-100字核心成果摘要"
    }
]

def insert_attachments():
    """插入所有附件到数据库"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    for f in files:
        if os.path.exists(f["path"]):
            file_size = os.path.getsize(f["path"])
            url = f"output/task-1716/{f['filename']}"
            
            # 检查是否已存在
            cursor.execute(
                "SELECT id FROM attachments WHERE entity_type = %s AND entity_id = %s AND filename = %s",
                ("task", 1716, f["filename"])
            )
            exists = cursor.fetchone()
            
            if exists:
                print(f"⚠️  附件已存在，跳过: {f['filename']}")
            else:
                cursor.execute("""
                    INSERT INTO attachments (entity_type, entity_id, filename, url, size, file_type, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, NOW())
                """, ("task", 1716, f["filename"], url, file_size, f["file_type"]))
                print(f"✅ 附件已上传: {f['filename']} ({file_size} bytes)")
        else:
            print(f"❌ 文件不存在: {f['path']}")
    
    conn.commit()
    conn.close()

def update_task_status():
    """更新任务状态为completed"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 读取执行日志和结果摘要
    with open("/Users/mettlyz/.openclaw/workspace/output/task-1716/任务1716_执行日志.md", "r", encoding="utf-8") as f:
        execution_log = f.read()
    
    with open("/Users/mettlyz/.openclaw/workspace/output/task-1716/任务1716_结果摘要.md", "r", encoding="utf-8") as f:
        result_summary = f.read()
    
    with open("/Users/mettlyz/.openclaw/workspace/output/task-1716/任务1716_任务摘要.md", "r", encoding="utf-8") as f:
        task_summary = f.read()
    
    # 更新数据库
    cursor.execute("""
        UPDATE tasks 
        SET status = %s, 
            execution_log = %s, 
            result_summary = %s,
            task_summary = %s,
            updated_at = NOW()
        WHERE id = %s
    """, ("completed", execution_log, result_summary, task_summary, 1716))
    
    affected_rows = cursor.rowcount
    conn.commit()
    conn.close()
    
    if affected_rows > 0:
        print(f"✅ 任务状态已更新为: completed (ID: 1716)")
        print(f"   执行日志字数: {len(execution_log)}")
        print(f"   结果摘要字数: {len(result_summary)}")
        print(f"   任务摘要字数: {len(task_summary)}")
    else:
        print(f"⚠️  任务未更新或ID不存在: 1716")

if __name__ == "__main__":
    print("=" * 60)
    print("任务1716 数据库更新脚本")
    print("=" * 60)
    
    print("\n📁 开始插入附件...")
    insert_attachments()
    
    print("\n🔄 开始更新任务状态...")
    update_task_status()
    
    print("\n" + "=" * 60)
    print("✅ 所有操作完成！")
    print("=" * 60)
