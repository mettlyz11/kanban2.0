#!/usr/bin/env python3
"""
创建目标管理数据库结构并关联人生目标
"""
import sqlite3
import json
from datetime import datetime

conn = sqlite3.connect('/Users/mettlyz/.openclaw/workspace/kanban-react/backend/kanban_v5.db')
c = conn.cursor()

# 1. 创建人生目标表 (LifeGoals)
c.execute('''
    CREATE TABLE IF NOT EXISTS life_goals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        description TEXT,
        progress INTEGER DEFAULT 0,
        status TEXT DEFAULT 'active',
        priority INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')

# 2. 创建项目目标关联表 (ProjectGoals)
c.execute('''
    CREATE TABLE IF NOT EXISTS project_goals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        project_id INTEGER NOT NULL,
        life_goal_code TEXT NOT NULL,
        alignment_score INTEGER DEFAULT 100,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (project_id) REFERENCES projects (id),
        FOREIGN KEY (life_goal_code) REFERENCES life_goals (code)
    )
''')

# 3. 创建目标进度历史表
c.execute('''
    CREATE TABLE IF NOT EXISTS goal_progress_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        life_goal_code TEXT NOT NULL,
        progress INTEGER NOT NULL,
        recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (life_goal_code) REFERENCES life_goals (code)
    )
''')

# 4. 插入人生目标数据 (T1-T7)
life_goals = [
    ('T1', 'AI优化 (效率提升)', '通过AI工具和方法提升工作和学习效率', 65),
    ('T2', '和光智成 (创业)', 'AI材料研发平台，2026年7月融资目标', 40),
    ('T3', '学术竞争力 (T109平台)', '过渡态计算平台，打造学术影响力', 95),
    ('T4', '财务增值', '股票、房产、投资增值', 0),
    ('T5', '家庭幸福', '家庭和谐、子女教育、健康管理', 0),
    ('T6', '诉讼相关', '九原区纠纷等法律事务处理', 0),
    ('T7', '身心健康', '身体健康、心理健康、生活品质', 0),
]

for code, name, desc, progress in life_goals:
    c.execute('''
        INSERT OR REPLACE INTO life_goals (code, name, description, progress, status, priority)
        VALUES (?, ?, ?, ?, 'active', ?)
    ''', (code, name, desc, progress, int(code[1])))

print(f"✅ 插入/更新 {len(life_goals)} 个人生目标")

# 5. 关联项目与人生目标
# 先获取所有项目
project_mappings = [
    (2, 'T3'),   # T109 -> T3 学术竞争力
    (3, 'T2'),   # Pepi -> T2 和光智成 (创业)
    (4, 'T2'),   # 和光智成 -> T2
    (5, 'T3'),   # AI框架 -> T3
    (6, 'T2'),   # 数字人 -> T2
    (7, 'T1'),   # 知识大脑 -> T1 AI优化
    (8, 'T1'),   # 看板系统 -> T1 AI优化
]

# 清空现有映射
c.execute("DELETE FROM project_goals")

for project_id, goal_code in project_mappings:
    try:
        c.execute('''
            INSERT INTO project_goals (project_id, life_goal_code, alignment_score)
            VALUES (?, ?, 100)
        ''', (project_id, goal_code))
    except Exception as e:
        print(f"⚠️ 项目 {project_id} 映射失败: {e}")

print(f"✅ 关联 {len(project_mappings)} 个项目到人生目标")

# 6. 更新目标进度历史
c.execute("DELETE FROM goal_progress_history")
for code, name, desc, progress in life_goals:
    c.execute('''
        INSERT INTO goal_progress_history (life_goal_code, progress, recorded_at)
        VALUES (?, ?, ?)
    ''', (code, progress, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

print(f"✅ 记录目标进度历史")

conn.commit()
conn.close()

print("\n🎉 目标管理系统初始化完成!")
print("\n人生目标概览:")
for code, name, desc, progress in life_goals:
    print(f"  {code}: {name} - 进度 {progress}%")
