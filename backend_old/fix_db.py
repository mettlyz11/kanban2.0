#!/usr/bin/env python3
"""
数据库修复脚本 - 创建缺失的表
"""
import sqlite3
import os

def init_goals_tables(db_path):
    """初始化目标相关表"""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # 创建goals表
    c.execute('''
        CREATE TABLE IF NOT EXISTS goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            category TEXT DEFAULT 'product',
            progress INTEGER DEFAULT 0,
            status TEXT DEFAULT 'todo',
            deadline DATE,
            project_count INTEGER DEFAULT 0,
            task_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 创建key_results表
    c.execute('''
        CREATE TABLE IF NOT EXISTS key_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            goal_id INTEGER,
            description TEXT NOT NULL,
            target_value REAL DEFAULT 100,
            current_value REAL DEFAULT 0,
            unit TEXT DEFAULT '%',
            status TEXT DEFAULT 'todo',
            FOREIGN KEY (goal_id) REFERENCES goals (id)
        )
    ''')
    
    # 检查是否已有数据
    c.execute('SELECT COUNT(*) FROM goals')
    count = c.fetchone()[0]
    
    if count == 0:
        # 添加示例目标数据
        sample_goals = [
            ('T109过渡态计算平台', '打造世界领先的AI驱动计算化学平台', 'product', 65, 'progress'),
            ('Pepi数字人系统', '构建智能数字员工 ecosystem', 'product', 40, 'progress'),
            ('AI Agent框架', '开发企业级AI智能体框架', 'technology', 95, 'progress'),
            ('和光智成品牌', '建立AI材料研发品牌影响力', 'business', 70, 'progress'),
        ]
        
        for title, desc, cat, prog, status in sample_goals:
            c.execute('''
                INSERT INTO goals (title, description, category, progress, status, project_count, task_count)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (title, desc, cat, prog, status, 3, 12))
        
        print(f"✅ 添加了 {len(sample_goals)} 个示例目标")
    
    conn.commit()
    conn.close()
    print("✅ goals 表和 key_results 表已创建")

def init_system_history(db_path):
    """初始化系统监控历史表"""
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # 创建system_metrics_history表（如果不存在）
    c.execute('''
        CREATE TABLE IF NOT EXISTS system_metrics_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            cpu_percent REAL,
            memory_percent REAL,
            disk_percent REAL,
            network_sent INTEGER,
            network_recv INTEGER
        )
    ''')
    
    conn.commit()
    conn.close()
    print("✅ system_metrics_history 表已创建")

if __name__ == '__main__':
    db_path = '/opt/kanban-react/backend/kanban_v5.db'
    
    if os.path.exists(db_path):
        init_goals_tables(db_path)
        init_system_history(db_path)
        print("\n🎉 数据库修复完成!")
    else:
        print(f"❌ 数据库不存在: {db_path}")
