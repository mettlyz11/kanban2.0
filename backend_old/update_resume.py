#!/usr/bin/env python3
"""更新刘宇宙简历信息到看板数据库"""
import sqlite3
import json
import sys

conn = sqlite3.connect('/opt/kanban-react/backend/kanban_v5.db')
cursor = conn.cursor()

# 更新电话
cursor.execute("UPDATE contacts SET phone = ? WHERE name = ?", 
               ('15210365033', '刘宇宙'))

# 更新邮箱（添加第二邮箱到metadata字段）
cursor.execute("SELECT metadata FROM contacts WHERE name = '刘宇宙'")
row = cursor.fetchone()
metadata = json.loads(row[0]) if row and row[0] else {}
metadata['email_secondary'] = 'liuyuzhou@deepchem.cn'
metadata['awards'] = [
    '中关村前沿大赛智能制造与新材料第四名 (2022)',
    'AI金雁奖应用创新大奖 (2022)', 
    '保尔森奖十大提名项目 (2022)',
    '国家高层次人才青年项目获得者 (2014)'
]
metadata['papers'] = [
    'Cage-Confined CuO Nanoparticles (Small Methods 2025)',
    'Atomically Dispersed Mn-Ir Sites (Small 2024)',
    'Nano Si-doped Ruthenium Oxide (Adv. Sci. 2023)'
]

cursor.execute("UPDATE contacts SET metadata = ? WHERE name = ?",
               (json.dumps(metadata, ensure_ascii=False), '刘宇宙'))

conn.commit()
conn.close()

print('✅ 刘宇宙简历信息更新完成')
print('  - 电话: 15210365033')
print('  - 第二邮箱: liuyuzhou@deepchem.cn')
print('  - 奖项: 4个')
print('  - 论文: 3篇')
