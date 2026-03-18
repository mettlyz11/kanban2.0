#!/usr/bin/env python3
"""
更新看板 3.0 个人信息和公司信息
- 更新刘宇宙个人信息（entities 表）
- 更新公司信息（company_info 表）
"""

import sqlite3
import json
from datetime import datetime

DB_PATH = 'kanban_v5.db'

def update_liuyuzhou_entity():
    """更新 entities 表中刘宇宙的信息"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 丰富的 metadata 信息
    metadata = {
        "role": "创始人/CEO",
        "org": "和光智成",
        "birth_date": "1982-09-16",
        "gender": "男",
        "education": [
            {
                "school": "北京大学",
                "degree": "博士",
                "major": "物理化学",
                "year": "2010"
            }
        ],
        "work_experience": [
            {
                "company": "北京航空航天大学",
                "position": "蓝天青年学者（二级）",
                "department": "化学学院",
                "start_date": "2025-09-01",
                "end_date": "2030-08-31",
                "type": "academic"
            },
            {
                "company": "北京和光智成科技有限公司",
                "position": "创始人、CEO",
                "start_date": "2023-01-01",
                "type": "entrepreneurship"
            },
            {
                "company": "北京深云智合科技有限公司",
                "position": "法定代表人/董事长",
                "start_date": "2020-11-09",
                "end_date": "present",
                "type": "entrepreneurship"
            }
        ],
        "research_areas": [
            "计算化学",
            "分子模拟",
            "AI 驱动的化学研究",
            "高分子材料",
            "材料智能研发"
        ],
        "awards": [
            {
                "name": "蓝天青年学者",
                "year": "2025",
                "organization": "北京航空航天大学"
            }
        ],
        "papers": [
            {
                "title": "Nature 论文（高分子研究）",
                "journal": "Nature",
                "year": "待补充",
                "role": "第一作者/通讯作者"
            },
            {
                "title": "JACS 论文（高分子研究）",
                "journal": "Journal of the American Chemical Society",
                "year": "待补充",
                "role": "第一作者/通讯作者"
            }
        ],
        "patents": [
            {
                "title": "AI 分子生成算法相关专利",
                "status": "申请中",
                "year": "2026",
                "application_number": "待补充"
            }
        ],
        "network": {
            "outgoing": [
                {"target": "和光智成", "type": "founder_of", "desc": "创始人/CEO"},
                {"target": "深云智合", "type": "legal_representative", "desc": "法定代表人"},
                {"target": "北航", "type": "works_at", "desc": "蓝天青年学者"}
            ],
            "incoming": [],
            "total_connections": 3,
            "last_sync": datetime.now().isoformat()
        },
        "synced_at": datetime.now().isoformat()
    }
    
    # 先检查是否存在
    cursor.execute('SELECT id FROM entities WHERE name = ? AND entity_type = ?', ('刘宇宙', 'person'))
    existing = cursor.fetchone()
    
    if existing:
        # 更新现有记录
        cursor.execute('''
            UPDATE entities 
            SET description = ?, metadata = ?
            WHERE name = '刘宇宙' AND entity_type = 'person'
        ''', (
            '北航化学学院蓝天青年学者 / 和光智成创始人&CEO / 深云智合法定代表人',
            json.dumps(metadata, ensure_ascii=False)
        ))
        print(f"✓ 更新 entities 表：{cursor.rowcount} 行受影响")
    else:
        # 插入新记录
        cursor.execute('''
            INSERT INTO entities (name, entity_type, description, metadata)
            VALUES (?, ?, ?, ?)
        ''', (
            '刘宇宙',
            'person',
            '北航化学学院蓝天青年学者 / 和光智成创始人&CEO / 深云智合法定代表人',
            json.dumps(metadata, ensure_ascii=False)
        ))
        print(f"✓ 插入 entities 表：{cursor.rowcount} 行受影响")
    
    conn.commit()
    conn.close()

def update_company_info():
    """更新 company_info 表中的公司信息"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 更新和光智成
    cursor.execute('''
        UPDATE company_info 
        SET short_name = ?, legal_representative = ?, industry = ?, 
            create_date = ?, description = ?
        WHERE name = '和光智成（北京）科技有限公司' OR name = '北京和光智成科技有限公司'
    ''', (
        '和光智成',
        '刘宇宙',
        '人工智能/材料科学',
        '2023-01-01',
        '材料研发新范式 - "生成式 AI 分子计算平台 + 高通量机器人实验室+AI 化学数据基建"全闭环。注册资本 500 万元，估值目标 2026 年 6 月 5 亿元。核心产品：Yun 蕴算（AI 分子计算平台）、XuanLab 玄基（高通量机器人实验室）。'
    ))
    print(f"✓ 更新和光智成：{cursor.rowcount} 行受影响")
    
    # 更新深云智合
    cursor.execute('''
        UPDATE company_info 
        SET short_name = ?, legal_representative = ?, industry = ?, 
            create_date = ?, description = ?
        WHERE name = '北京深云智合科技有限公司'
    ''', (
        '深云智合',
        '刘宇宙',
        'IT 服务/化工/AI 材料',
        '2020-11-09',
        '成立于 2020 年 11 月，注册资本 401.02 万元。量子化学计算云平台运营商，AI 与分子合成深度结合。2023 年与包头九原区合作建设"黑灯实验室"，2024 年 6 月正式投产。'
    ))
    print(f"✓ 更新深云智合：{cursor.rowcount} 行受影响")
    
    conn.commit()
    conn.close()

if __name__ == '__main__':
    print("开始更新看板 3.0 个人信息和公司信息...")
    print("=" * 60)
    
    update_liuyuzhou_entity()
    update_company_info()
    
    print("=" * 60)
    print("✓ 所有更新完成！")
