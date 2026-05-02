#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""查询看板当前状态"""

import sys
sys.path.insert(0, '/Users/mettlyz/.openclaw/workspace/scripts')
from lib.db_connector import execute_query

# T1-T7 定义
TARGETS = {
    'T1': 'AI助手优化',
    'T2': '和光智成商业成功', 
    'T3': '学术影响力',
    'T4': '财富增值',
    'T5': '家庭幸福',
    'T6': '社会工作', 
    'T7': '身心健康'
}

def main():
    # 查询各目标的pending任务数
    print('=== T1-T7 各目标 pending 任务数 ===')
    for code, name in TARGETS.items():
        result = execute_query('''
            SELECT COUNT(*) as cnt FROM tasks 
            WHERE status IN ('pending', 'in_progress') 
            AND title LIKE %s
        ''', (f'{code}:%',))
        cnt_val = result[0]['cnt'] if result else 0
        print(f'{code}: {name} - pending: {cnt_val}')

    # 查询过去24小时各目标生成的任务数
    print('\n=== 过去24小时各目标 auto_generated 任务数 ===')
    for code, name in TARGETS.items():
        result = execute_query('''
            SELECT COUNT(*) as cnt FROM tasks 
            WHERE task_type LIKE 'auto_generated_v4.%'
            AND created_at >= NOW() - INTERVAL 24 HOUR
            AND title LIKE %s
        ''', (f'{code}:%',))
        cnt_val = result[0]['cnt'] if result else 0
        print(f'{code}: {name} - 24h生成: {cnt_val}')

    # 查询所有现有任务标题用于去重
    print('\n=== 现有任务标题（前50字）===')
    result = execute_query('''
        SELECT id, title FROM tasks 
        WHERE status IN ('pending', 'completed', 'done', 'in_progress')
        ORDER BY id DESC LIMIT 100
    ''')
    for r in result:
        print(f'#{r["id"]}: {r["title"][:50]}')

if __name__ == '__main__':
    main()
