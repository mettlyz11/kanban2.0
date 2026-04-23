#!/usr/bin/env python3
"""
创建 workflow_architecture 数据库表
用于存储可编辑的 Dudu 工作流程架构图
"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'kanban_v5.db')

def create_workflow_architecture_tables():
    """创建 workflow_architecture 相关表"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # 创建节点表
    c.execute('''
        CREATE TABLE IF NOT EXISTS workflow_architecture (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type TEXT DEFAULT 'node',
            x INTEGER DEFAULT 0,
            y INTEGER DEFAULT 0,
            color TEXT DEFAULT '#e3f2fd',
            file_path TEXT,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 创建连接关系表
    c.execute('''
        CREATE TABLE IF NOT EXISTS workflow_connections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            from_node INTEGER NOT NULL,
            to_node INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (from_node) REFERENCES workflow_architecture(id),
            FOREIGN KEY (to_node) REFERENCES workflow_architecture(id)
        )
    ''')
    
    # 创建版本历史表
    c.execute('''
        CREATE TABLE IF NOT EXISTS workflow_architecture_versions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            version INTEGER NOT NULL,
            nodes_json TEXT NOT NULL,
            connections_json TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            description TEXT
        )
    ''')
    
    # 插入默认节点数据
    default_nodes = [
        ('用户输入', 'node', 80, 100, '#e3f2fd', '', '接收用户指令和任务'),
        ('SOUL.md', 'file', 220, 100, '#fff3e0', 'SOUL.md', '身份定义和人格'),
        ('USER.md', 'file', 360, 100, '#e8f5e9', 'USER.md', '用户档案和偏好'),
        ('AGENTS.md', 'file', 500, 100, '#fce4ec', 'AGENTS.md', '执行准则'),
        ('standards.md', 'file', 640, 100, '#f3e5f5', 'standards.md', '标准规范'),
        ('任务执行', 'node', 780, 100, '#f3e5f5', '', '执行具体任务'),
        ('MEMORY.md', 'file', 200, 260, '#e0f2f1', 'MEMORY.md', '长期记忆存储'),
        ('结果输出', 'node', 400, 260, '#e8eaf6', '', '输出执行结果'),
        ('HEARTBEAT.md', 'file', 600, 260, '#fff8e1', 'HEARTBEAT.md', '定时检查'),
    ]
    
    # 检查是否已有数据
    c.execute('SELECT COUNT(*) FROM workflow_architecture')
    count = c.fetchone()[0]
    
    if count == 0:
        c.executemany('''
            INSERT INTO workflow_architecture (name, type, x, y, color, file_path, description)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', default_nodes)
        
        # 插入默认连接关系
        default_connections = [
            (1, 2), (2, 3), (3, 4), (4, 5), (5, 6),  # 输入层连接
            (6, 6),  # 任务执行自连接
            (6, 7), (6, 8), (6, 9),  # 执行层连接
            (7, 8), (8, 9),  # 输出层连接
        ]
        
        c.executemany('''
            INSERT INTO workflow_connections (from_node, to_node)
            VALUES (?, ?)
        ''', default_connections)
        
        # 创建初始版本
        c.execute('''
            INSERT INTO workflow_architecture_versions (version, nodes_json, connections_json, description)
            VALUES (1, ?, ?, ?)
        ''', ('[]', '[]', '初始版本'))
    
    conn.commit()
    conn.close()
    
    print("✅ workflow_architecture 数据库表创建成功")
    print(f"   - workflow_architecture: 节点表")
    print(f"   - workflow_connections: 连接关系表")
    print(f"   - workflow_architecture_versions: 版本历史表")
    print(f"   - 已插入 {len(default_nodes)} 个默认节点")

if __name__ == '__main__':
    create_workflow_architecture_tables()
