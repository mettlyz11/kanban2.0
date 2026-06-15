#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
任务 #1998 数据库更新脚本
更新任务状态、执行日志，并上传附件
"""

import os
import sys
import sqlite3
from datetime import datetime

# 数据库路径
DB_PATH = os.path.expanduser("~/.openclaw/data/kanban.db")

def get_db_connection():
    """获取数据库连接"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """初始化数据库表（如果不存在）"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 创建tasks表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            status TEXT DEFAULT 'pending',
            execution_log TEXT,
            result_summary TEXT,
            task_summary TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 创建attachments表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS attachments (
            id INTEGER PRIMARY KEY,
            task_id INTEGER,
            filename TEXT NOT NULL,
            file_path TEXT NOT NULL,
            file_size INTEGER,
            file_type TEXT,
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (task_id) REFERENCES tasks (id)
        )
    ''')
    
    conn.commit()
    return conn

def update_task():
    """更新任务 #1998的状态和内容"""
    conn = init_db()
    cursor = conn.cursor()
    
    task_id = 1998
    output_dir = "/Users/mettlyz/.openclaw/workspace/output/task-1998"
    
    # 读取执行日志
    with open(os.path.join(output_dir, "execution_log.md"), 'r', encoding='utf-8') as f:
        execution_log = f.read()
    
    # 读取结果摘要
    with open(os.path.join(output_dir, "result_summary.md"), 'r', encoding='utf-8') as f:
        result_summary = f.read()
    
    # 读取任务摘要
    with open(os.path.join(output_dir, "task_summary.md"), 'r', encoding='utf-8') as f:
        task_summary = f.read()
    
    # 检查任务是否存在
    cursor.execute("SELECT id FROM tasks WHERE id = ?", (task_id,))
    exists = cursor.fetchone()
    
    if exists:
        # 更新现有任务
        cursor.execute('''
            UPDATE tasks 
            SET status = ?, 
                execution_log = ?, 
                result_summary = ?, 
                task_summary = ?,
                updated_at = ?
            WHERE id = ?
        ''', ('completed', execution_log, result_summary, task_summary, 
              datetime.now(), task_id))
        # print(f"✅ 任务 #{task_id} 已更新")
    else:
        # 插入新任务
        cursor.execute('''
            INSERT INTO tasks (id, title, status, execution_log, result_summary, task_summary, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (task_id, 'T7: 身心健康与效能提升 - 2026无感健康监测体系搭建方案', 
              'completed', execution_log, result_summary, task_summary, datetime.now()))
        # print(f"✅ 任务 #{task_id} 已创建")
    
    # 上传附件
    attachments = [
        ("无感健康设备对比评估报告_调研分析_20260426.md", "调研分析报告"),
        ("个人健康监测体系架构设计_架构方案_20260426.md", "架构设计方案"),
        ("2026年度高管健康管理全方案_管理方案_20260426.md", "管理方案"),
        ("健康投入效能提升量化测算模型_测算模型_20260426.md", "测算模型")
    ]
    
    for filename, file_type in attachments:
        file_path = os.path.join(output_dir, filename)
        file_size = os.path.getsize(file_path)
        
        cursor.execute('''
            INSERT INTO attachments (task_id, filename, file_path, file_size, file_type)
            VALUES (?, ?, ?, ?, ?)
        ''', (task_id, filename, file_path, file_size, file_type))
        
        # print(f"✅ 附件已上传: {filename} ({file_size} 字节)")
    
    conn.commit()
    conn.close()
    
    # print("\n🎉 数据库更新完成！")
    # print(f"   - 任务 #{task_id} 状态: completed")
    # print(f"   - 附件数量: {len(attachments)} 个")

if __name__ == "__main__":
    update_task()
