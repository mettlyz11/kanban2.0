#!/usr/bin/env python3
"""
看板系统 v2.4.13 验证脚本
检查所有 SQLite 引用是否已移除
"""

import os
import sys

BACKEND_DIR = '/opt/kanban-react/backend'

# 核心文件列表
CORE_FILES = [
    'app.py',
    'db_config.py',
    'task_worker.py',
    '.env',
]

def check_sqlite_references():
    """检查 SQLite 引用"""
    print("=" * 60)
    print("🔍 检查 SQLite 引用")
    print("=" * 60)
    
    issues = []
    
    for filename in CORE_FILES:
        filepath = os.path.join(BACKEND_DIR, filename)
        if not os.path.exists(filepath):
            print(f"⚠️  文件不存在：{filename}")
            continue
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查实际的 SQLite 代码引用（排除注释）
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            # 跳过纯注释
            if line.strip().startswith('#'):
                continue
            
            # 检查代码中的 SQLite 引用
            if 'import sqlite3' in line or 'sqlite3.' in line:
                issues.append(f"{filename}:{i} - 代码引用：{line.strip()}")
    
    if issues:
        print("❌ 发现 SQLite 代码引用:")
        for issue in issues:
            print(f"  {issue}")
        return False
    else:
        print("✅ 核心文件无 SQLite 代码引用")
        return True

def check_mysql_config():
    """检查 MySQL 配置"""
    print("\n" + "=" * 60)
    print("🔍 检查 MySQL 配置")
    print("=" * 60)
    
    try:
        sys.path.insert(0, BACKEND_DIR)
        from db_config import MYSQL_CONFIG, get_connection
        
        print(f"✅ MySQL 配置存在")
        print(f"   Host: {MYSQL_CONFIG['host']}")
        print(f"   Database: {MYSQL_CONFIG['database']}")
        
        # 测试连接
        try:
            conn = get_connection()
            conn.close()
            print("✅ 数据库连接测试通过")
            return True
        except Exception as e:
            print(f"⚠️  数据库连接失败：{e}")
            return False
    except Exception as e:
        print(f"❌ MySQL 配置加载失败：{e}")
        return False

def check_database_schema():
    """检查数据库表结构"""
    print("\n" + "=" * 60)
    print("🔍 检查数据库表结构")
    print("=" * 60)
    
    try:
        sys.path.insert(0, BACKEND_DIR)
        from db_config import get_connection
        
        conn = get_connection()
        cursor = conn.cursor()
        
        # 检查 tasks 表字段
        cursor.execute("DESCRIBE tasks")
        columns = [row[0] for row in cursor.fetchall()]
        
        required_columns = ['slurm_job_id', 'slurm_output_file', 'retry_count']
        missing = [col for col in required_columns if col not in columns]
        
        if missing:
            print(f"❌ 缺少字段：{missing}")
            return False
        else:
            print("✅ tasks 表包含所有必需字段")
            print(f"   - slurm_job_id: {'✓' if 'slurm_job_id' in columns else '✗'}")
            print(f"   - slurm_output_file: {'✓' if 'slurm_output_file' in columns else '✗'}")
            print(f"   - retry_count: {'✓' if 'retry_count' in columns else '✗'}")
            return True
    except Exception as e:
        print(f"❌ 数据库检查失败：{e}")
        return False

def main():
    print("\n" + "=" * 60)
    print("📋 看板系统 v2.4.13 验证报告")
    print("=" * 60)
    
    results = {
        'sqlite_check': check_sqlite_references(),
        'mysql_config': check_mysql_config(),
        'database_schema': check_database_schema(),
    }
    
    print("\n" + "=" * 60)
    print("📊 验证总结")
    print("=" * 60)
    
    all_passed = all(results.values())
    
    for check, passed in results.items():
        status = "✅" if passed else "❌"
        print(f"{status} {check}: {'通过' if passed else '失败'}")
    
    if all_passed:
        print("\n🎉 所有检查通过！v2.4.13 部署成功！")
        return 0
    else:
        print("\n⚠️  部分检查未通过，请检查上述报告")
        return 1

if __name__ == '__main__':
    sys.exit(main())
