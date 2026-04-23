#!/usr/bin/env python3
# record_version.py - 自动记录部署版本
# 用法：python3 record_version.py <project> <version> [notes]

import sqlite3
import sys
import os
from datetime import datetime
import subprocess

def get_git_commit():
    """获取当前 Git 提交哈希"""
    try:
        result = subprocess.run(['git', 'rev-parse', '--short', 'HEAD'],
                              capture_output=True, text=True, cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        return result.stdout.strip()
    except:
        return 'unknown'

def record_version(project, version, notes=''):
    """记录部署版本到数据库"""
    
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'kanban_v5.db')
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    git_commit = get_git_commit()
    deployed_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    cursor.execute('''
        INSERT INTO deployment_versions (project, version, git_commit, notes, deployed_at)
        VALUES (?, ?, ?, ?, ?)
    ''', (project, version, git_commit, notes, deployed_at))
    
    conn.commit()
    
    # 获取刚插入的记录
    cursor.execute('SELECT * FROM deployment_versions WHERE id = last_insert_rowid()')
    record = cursor.fetchone()
    
    conn.close()
    
    return {
        'id': record[0],
        'project': record[1],
        'version': record[2],
        'deployed_at': record[3],
        'git_commit': record[4],
        'notes': record[5]
    }

def get_latest_versions():
    """获取所有项目的最新版本"""
    
    db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'kanban_v5.db')
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT project, version, deployed_at, git_commit, notes
        FROM deployment_versions dv1
        WHERE deployed_at = (
            SELECT MAX(deployed_at)
            FROM deployment_versions dv2
            WHERE dv2.project = dv1.project
        )
    ''')
    
    versions = {}
    for row in cursor.fetchall():
        versions[row[0]] = {
            'version': row[1],
            'deployed_at': row[2],
            'git_commit': row[3],
            'notes': row[4]
        }
    
    conn.close()
    return versions

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print("用法：python3 record_version.py <project> <version> [notes]")
        print("示例：python3 record_version.py t109 v2.4.15 '修复 404 错误'")
        sys.exit(1)
    
    project = sys.argv[1]
    version = sys.argv[2]
    notes = sys.argv[3] if len(sys.argv) > 3 else ''
    
    result = record_version(project, version, notes)
    
    print(f"✅ 版本已记录:")
    print(f"   项目：{result['project']}")
    print(f"   版本：{result['version']}")
    print(f"   时间：{result['deployed_at']}")
    print(f"   提交：{result['git_commit']}")
    print(f"   说明：{result['notes']}")
