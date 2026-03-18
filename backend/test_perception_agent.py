#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
感知 Agent 功能测试脚本
测试所有 API 端点和数据库功能
"""

import sqlite3
import json
import hashlib
from datetime import datetime
from pathlib import Path

# 颜色定义
class Colors:
    GREEN = '\033[0;32m'
    RED = '\033[0;31m'
    YELLOW = '\033[1;33m'
    NC = '\033[0m'  # No Color

def print_header(text):
    print(f"\n{Colors.GREEN}{'='*60}{Colors.NC}")
    print(f"{Colors.GREEN}{text}{Colors.NC}")
    print(f"{Colors.GREEN}{'='*60}{Colors.NC}\n")

def print_success(text):
    print(f"{Colors.GREEN}✅ {text}{Colors.NC}")

def print_error(text):
    print(f"{Colors.RED}❌ {text}{Colors.NC}")

def print_info(text):
    print(f"{Colors.YELLOW}ℹ️  {text}{Colors.NC}")

# 数据库路径
DB_PATH = Path.home() / '.openclaw' / 'workspace' / 'kanban-react' / 'backend' / 'kanban_v5.db'

def test_database_connection():
    """测试 1: 数据库连接"""
    print_header("测试 1: 数据库连接")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        conn.close()
        print_success(f"数据库连接成功：{DB_PATH}")
        return True
    except Exception as e:
        print_error(f"数据库连接失败：{e}")
        return False

def test_perception_events_table():
    """测试 2: perception_events 表存在"""
    print_header("测试 2: perception_events 表结构")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 检查表是否存在
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='perception_events'")
        if not cursor.fetchone():
            print_error("perception_events 表不存在")
            conn.close()
            return False
        
        print_success("perception_events 表存在")
        
        # 获取表结构
        cursor.execute("PRAGMA table_info(perception_events)")
        columns = cursor.fetchall()
        
        print_info("表结构:")
        for col in columns:
            print(f"  - {col[1]} ({col[2]})")
        
        # 检查索引
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='perception_events'")
        indexes = cursor.fetchall()
        
        if indexes:
            print_info("索引:")
            for idx in indexes:
                print(f"  - {idx[0]}")
        
        conn.close()
        print_success("表结构验证通过")
        return True
        
    except Exception as e:
        print_error(f"表结构验证失败：{e}")
        return False

def test_insert_event():
    """测试 3: 插入事件"""
    print_header("测试 3: 插入测试事件")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # 插入测试事件
        hash_str = hashlib.md5(f"test_auto_test{datetime.now()}".encode()).hexdigest()[:16]
        
        cursor.execute('''
            INSERT INTO perception_events 
            (event_type, severity, source, message, metadata, timestamp, hash)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            'test', 'low', 'test_script',
            '自动化测试事件',
            json.dumps({'test_id': 1, 'automated': True}),
            datetime.now().isoformat(),
            hash_str
        ))
        
        conn.commit()
        event_id = cursor.lastrowid
        
        # 验证插入
        cursor.execute('SELECT * FROM perception_events WHERE id = ?', (event_id,))
        row = cursor.fetchone()
        
        if row:
            print_success(f"事件插入成功 (ID: {event_id})")
            print_info(f"  类型：{row[1]}")
            print_info(f"  级别：{row[2]}")
            print_info(f"  来源：{row[3]}")
            print_info(f"  消息：{row[4]}")
        else:
            print_error("无法查询到刚插入的事件")
            conn.close()
            return False
        
        conn.close()
        print_success("事件插入测试通过")
        return True
        
    except Exception as e:
        print_error(f"事件插入失败：{e}")
        return False

def test_query_events():
    """测试 4: 查询事件"""
    print_header("测试 4: 查询事件")
    
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # 查询最近 5 个事件
        cursor.execute('''
            SELECT id, event_type, severity, source, message, timestamp
            FROM perception_events
            ORDER BY timestamp DESC
            LIMIT 5
        ''')
        
        rows = cursor.fetchall()
        
        if not rows:
            print_info("数据库中没有事件记录")
            conn.close()
            return True
        
        print_info(f"最近 {len(rows)} 个事件:")
        for row in rows:
            print(f"\n  ID: {row['id']}")
            print(f"  类型：{row['event_type']}")
            print(f"  级别：{row['severity']}")
            print(f"  来源：{row['source']}")
            print(f"  消息：{row['message']}")
            print(f"  时间：{row['timestamp']}")
        
        conn.close()
        print_success("事件查询测试通过")
        return True
        
    except Exception as e:
        print_error(f"事件查询失败：{e}")
        return False

def test_agent_running():
    """测试 5: 检查 Agent 是否运行"""
    print_header("测试 5: 感知 Agent 运行状态")
    
    import subprocess
    
    try:
        # 检查进程
        result = subprocess.run(
            ['pgrep', '-f', 'perception_agent.py'],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0 and result.stdout.strip():
            pids = result.stdout.strip().split('\n')
            print_success(f"感知 Agent 正在运行 (PID: {', '.join(pids)})")
            return True
        else:
            print_info("感知 Agent 未运行 (这是可选的)")
            return True  # 不强制要求运行
            
    except Exception as e:
        print_info(f"无法检查进程状态：{e}")
        return True

def test_config_file():
    """测试 6: 配置文件"""
    print_header("测试 6: 配置文件")
    
    config_path = Path.home() / '.openclaw' / 'workspace' / 'kanban-react' / 'backend' / 'perception_config.yml'
    
    if not config_path.exists():
        print_error(f"配置文件不存在：{config_path}")
        return False
    
    print_success(f"配置文件存在：{config_path}")
    
    try:
        import yaml
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        print_info("配置内容:")
        print(json.dumps(config, indent=2, ensure_ascii=False))
        print_success("配置文件格式正确")
        return True
        
    except ImportError:
        print_info("PyYAML 未安装，跳过 YAML 解析")
        return True
    except Exception as e:
        print_error(f"配置文件解析失败：{e}")
        return False

def main():
    """运行所有测试"""
    print_header("🧪 感知 Agent 功能测试")
    
    tests = [
        ("数据库连接", test_database_connection),
        ("表结构", test_perception_events_table),
        ("插入事件", test_insert_event),
        ("查询事件", test_query_events),
        ("Agent 状态", test_agent_running),
        ("配置文件", test_config_file),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print_error(f"{name} 测试异常：{e}")
            results.append((name, False))
    
    # 汇总结果
    print_header("📊 测试结果汇总")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = f"{Colors.GREEN}✅ 通过{Colors.NC}" if result else f"{Colors.RED}❌ 失败{Colors.NC}"
        print(f"{status} {name}")
    
    print(f"\n总计：{passed}/{total} 测试通过")
    
    if passed == total:
        print_success("🎉 所有测试通过！")
        return 0
    else:
        print_error(f"⚠️  {total - passed} 个测试失败")
        return 1

if __name__ == '__main__':
    exit(main())
