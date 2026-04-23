#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
感知 Agent 数据库初始化脚本
创建 perception_events 表
"""

import sqlite3
import os
from pathlib import Path

# 数据库路径
DB_PATH = Path.home() / '.openclaw' / 'workspace' / 'kanban-react' / 'backend' / 'kanban_v5.db'

def init_perception_events_table():
    """创建感知事件表"""
    
    if not os.path.exists(DB_PATH):
        print(f"❌ 数据库文件不存在：{DB_PATH}")
        return False
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 创建 perception_events 表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS perception_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                source TEXT NOT NULL,
                message TEXT NOT NULL,
                metadata TEXT DEFAULT '{}',
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                hash TEXT NOT NULL,
                processed BOOLEAN DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 创建索引以加速查询
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_perception_events_type 
            ON perception_events(event_type)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_perception_events_severity 
            ON perception_events(severity)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_perception_events_timestamp 
            ON perception_events(timestamp)
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_perception_events_hash 
            ON perception_events(hash)
        ''')
        
        conn.commit()
        conn.close()
        
        print(f"✅ 成功创建 perception_events 表")
        print(f"📂 数据库位置：{DB_PATH}")
        return True
        
    except Exception as e:
        print(f"❌ 创建表失败：{e}")
        return False

if __name__ == '__main__':
    print("🎯 初始化感知 Agent 数据库表...")
    init_perception_events_table()
