#!/usr/bin/env python3
"""
T109 后端健康检查脚本
检查后端服务、依赖、数据库连接和 API 状态
"""

import sqlite3
import os
import sys
import subprocess
from datetime import datetime

def check_service_status():
    """检查后端服务状态"""
    print("=" * 60)
    print("1. 后端服务状态检查")
    print("=" * 60)
    
    # 检查端口占用
    result = subprocess.run(['lsof', '-i', ':8086'], capture_output=True, text=True)
    if result.returncode == 0 and result.stdout:
        print("✅ 后端服务正在运行 (端口 8086)")
        print(f"   进程信息：{result.stdout.split()[0]}")
    else:
        print("❌ 后端服务未运行 (端口 8086 未被占用)")
        return False
    
    # 检查健康端点
    import urllib.request
    try:
        response = urllib.request.urlopen('http://localhost:8086/health', timeout=5)
        print("✅ 健康检查端点响应正常")
        return True
    except Exception as e:
        print(f"❌ 健康检查端点无法访问：{e}")
        return False

def check_dependencies():
    """检查后端依赖"""
    print("\n" + "=" * 60)
    print("2. 后端依赖检查")
    print("=" * 60)
    
    dependencies = {
        'flask': 'Flask',
        'flask_cors': 'Flask-CORS',
        'sqlite3': 'SQLite3'
    }
    
    all_ok = True
    for module, name in dependencies.items():
        try:
            __import__(module)
            print(f"✅ {name} 已安装")
        except ImportError:
            print(f"❌ {name} 未安装")
            all_ok = False
    
    # 检查 requirements.txt
    req_file = 'requirements.txt'
    if os.path.exists(req_file):
        print(f"\n✅ {req_file} 存在")
        with open(req_file, 'r') as f:
            print(f"   依赖数量：{len(f.readlines())} 个")
    else:
        print(f"\n❌ {req_file} 不存在")
        all_ok = False
    
    return all_ok

def check_database():
    """检查数据库连接"""
    print("\n" + "=" * 60)
    print("3. 数据库连接检查")
    print("=" * 60)
    
    db_path = 'kanban_v5.db'
    if not os.path.exists(db_path):
        print(f"❌ 数据库文件不存在：{db_path}")
        return False
    
    print(f"✅ 数据库文件存在：{db_path}")
    print(f"   文件大小：{os.path.getsize(db_path) / 1024 / 1024:.2f} MB")
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # 检查表数量
        cursor.execute('SELECT COUNT(*) FROM sqlite_master WHERE type="table"')
        table_count = cursor.fetchone()[0]
        print(f"✅ 数据库连接成功，表数量：{table_count}")
        
        # 检查关键表
        critical_tables = ['users', 'tasks', 'projects', 'api_keys']
        for table in critical_tables:
            cursor.execute(f'SELECT COUNT(*) FROM {table}')
            count = cursor.fetchone()[0]
            print(f"   - {table}: {count} 条记录")
        
        # 检查用户
        cursor.execute('SELECT COUNT(*) FROM users')
        user_count = cursor.fetchone()[0]
        print(f"\n✅ 用户总数：{user_count}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ 数据库连接失败：{e}")
        return False

def test_api():
    """测试 API 端点"""
    print("\n" + "=" * 60)
    print("4. API 端点测试")
    print("=" * 60)
    
    import urllib.request
    import json
    
    endpoints = [
        '/health',
        '/api/health',
    ]
    
    for endpoint in endpoints:
        try:
            response = urllib.request.urlopen(f'http://localhost:8086{endpoint}', timeout=5)
            data = json.loads(response.read().decode())
            print(f"✅ {endpoint}: {data.get('status', 'OK')}")
        except Exception as e:
            print(f"❌ {endpoint}: {str(e)}")

def generate_report():
    """生成检查报告"""
    print("\n" + "=" * 60)
    print("5. 后端状态总览")
    print("=" * 60)
    
    report = {
        'timestamp': datetime.now().isoformat(),
        'service_running': False,
        'dependencies_complete': False,
        'database_connected': False,
        'api_responsive': False
    }
    
    # 执行检查
    report['service_running'] = check_service_status()
    report['dependencies_complete'] = check_dependencies()
    report['database_connected'] = check_database()
    
    # API 测试（仅当服务运行时）
    if report['service_running']:
        test_api()
        report['api_responsive'] = True
    
    # 总结
    print("\n" + "=" * 60)
    print("📊 检查总结")
    print("=" * 60)
    
    checks = [
        ('后端服务', report['service_running']),
        ('依赖完整', report['dependencies_complete']),
        ('数据库连接', report['database_connected']),
        ('API 响应', report['api_responsive']),
    ]
    
    all_passed = True
    for name, passed in checks:
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"{name}: {status}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 后端状态正常，所有检查通过！")
    else:
        print("⚠️  后端存在异常，请检查上述失败项")
    print("=" * 60)
    
    return all_passed

if __name__ == '__main__':
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    success = generate_report()
    sys.exit(0 if success else 1)
