#!/usr/bin/env python3
"""
初始化文献调研记录数据库表
创建 research_logs 表用于存储文献调研记录
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'kanban_v5.db')

def init_research_logs_db():
    """创建 research_logs 表"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # 创建 research_logs 表
    c.execute('''
        CREATE TABLE IF NOT EXISTS research_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            project TEXT NOT NULL,
            query TEXT NOT NULL,
            papers_found INTEGER DEFAULT 0,
            key_findings TEXT,
            report_path TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 创建索引以提高查询性能
    c.execute('CREATE INDEX IF NOT EXISTS idx_research_logs_date ON research_logs(date)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_research_logs_project ON research_logs(project)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_research_logs_created_at ON research_logs(created_at)')
    
    conn.commit()
    conn.close()
    
    print("✅ research_logs 表创建成功")

if __name__ == '__main__':
    init_research_logs_db()
