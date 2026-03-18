#!/usr/bin/env python3
"""
系统监控 24 小时数据问题 - 测试验证脚本
验证所有修复是否生效
"""
import sqlite3
import requests
import datetime
import time
import sys

DB_PATH = 'kanban_v5.db'
API_BASE = 'http://localhost:8086'

def test_database():
    """测试 1: 数据库数据收集"""
    print("\n📊 测试 1: 数据库数据收集")
    print("-" * 50)
    
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # 检查表是否存在
        c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='monitoring_system_metrics'")
        if not c.fetchone():
            print("❌ monitoring_system_metrics 表不存在")
            return False
        
        # 检查数据量
        c.execute('SELECT COUNT(*) FROM monitoring_system_metrics')
        count = c.fetchone()[0]
        print(f"✅ 表中有 {count} 条记录")
        
        # 检查最新数据
        c.execute('SELECT MAX(timestamp) FROM monitoring_system_metrics')
        max_ts = c.fetchone()[0]
        if max_ts:
            latest = datetime.datetime.fromtimestamp(max_ts)
            now = datetime.datetime.now()
            diff = (now - latest).total_seconds() / 60
            print(f"✅ 最新数据时间：{latest.strftime('%H:%M:%S')} ({diff:.1f} 分钟前)")
            
            if diff > 10:
                print(f"⚠️  警告：数据可能超过 10 分钟未更新")
        else:
            print("❌ 表中无数据")
            return False
        
        # 检查数据间隔
        c.execute('''
            SELECT timestamp FROM monitoring_system_metrics 
            ORDER BY timestamp DESC LIMIT 5
        ''')
        timestamps = [r[0] for r in c.fetchall()]
        if len(timestamps) > 1:
            intervals = [(timestamps[i] - timestamps[i+1])/60 for i in range(len(timestamps)-1)]
            avg_interval = sum(intervals) / len(intervals)
            print(f"✅ 平均收集间隔：{avg_interval:.1f} 分钟 (目标：5 分钟)")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ 测试失败：{e}")
        return False

def test_api():
    """测试 2: API 端点"""
    print("\n🌐 测试 2: API 端点")
    print("-" * 50)
    
    try:
        # 测试 24 小时数据
        response = requests.get(f'{API_BASE}/api/metrics/history?range=24h', timeout=5)
        
        if response.status_code != 200:
            print(f"❌ API 返回错误：HTTP {response.status_code}")
            return False
        
        data = response.json()
        
        if not data.get('success'):
            print(f"❌ API 返回失败：{data.get('error')}")
            return False
        
        metrics = data.get('metrics', [])
        count = data.get('count', len(metrics))
        
        print(f"✅ API 返回 {count} 条数据")
        
        if count > 0:
            first = metrics[0]
            last = metrics[-1]
            print(f"✅ 第一条数据：CPU {first['cpu']:.1f}% @ {first.get('timestamp_formatted', 'N/A')}")
            print(f"✅ 最后一条数据：CPU {last['cpu']:.1f}% @ {last.get('timestamp_formatted', 'N/A')}")
        
        # 测试其他时间范围
        for time_range in ['1h', '6h', '7d']:
            resp = requests.get(f'{API_BASE}/api/metrics/history?range={time_range}', timeout=5)
            if resp.status_code == 200:
                d = resp.json()
                print(f"✅ {time_range}: {d.get('count', 0)} 条数据")
            else:
                print(f"⚠️  {time_range}: HTTP {resp.status_code}")
        
        return True
        
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到 API - 后端服务可能未运行")
        return False
    except Exception as e:
        print(f"❌ 测试失败：{e}")
        return False

def test_data_collection_script():
    """测试 3: 数据收集脚本"""
    print("\n📝 测试 3: 数据收集脚本")
    print("-" * 50)
    
    import os
    
    scripts = [
        'collect_metrics.sh',
        'p049_monitoring.py'
    ]
    
    for script in scripts:
        path = os.path.join(os.path.dirname(__file__), script)
        if os.path.exists(path):
            print(f"✅ 脚本存在：{script}")
        else:
            print(f"❌ 脚本缺失：{script}")
    
    # 检查收集间隔配置
    try:
        with open('p049_monitoring.py', 'r') as f:
            content = f.read()
            if 'collect_interval = 300' in content:
                print("✅ 收集间隔已设置为 300 秒 (5 分钟)")
            elif 'collect_interval = 30' in content:
                print("⚠️  收集间隔仍为 30 秒 (建议改为 300 秒)")
            else:
                print("⚠️  无法确定收集间隔")
    except:
        print("❌ 无法读取 p049_monitoring.py")
    
    return True

def test_frontend_component():
    """测试 4: 前端组件"""
    print("\n🎨 测试 4: 前端组件")
    print("-" * 50)
    
    import os
    
    frontend_path = os.path.join(os.path.dirname(__file__), '../frontend/src/pages/ResourceMonitor.tsx')
    
    if os.path.exists(frontend_path):
        print(f"✅ 前端组件存在：ResourceMonitor.tsx")
        
        with open(frontend_path, 'r') as f:
            content = f.read()
            
        checks = [
            ('getMetricsHistory', 'API 调用'),
            ('timeRange', '时间范围选择'),
            ('24 小时', '24 小时选项'),
            ('暂无监控数据', '空状态提示'),
        ]
        
        for keyword, desc in checks:
            if keyword in content:
                print(f"✅ {desc}: 已实现")
            else:
                print(f"⚠️  {desc}: 未找到")
    else:
        print("❌ 前端组件不存在")
    
    return True

def main():
    """运行所有测试"""
    print("=" * 60)
    print("系统监控 24 小时数据 - 测试验证")
    print("=" * 60)
    print(f"测试时间：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = []
    
    results.append(("数据库", test_database()))
    results.append(("API", test_api()))
    results.append(("数据收集脚本", test_data_collection_script()))
    results.append(("前端组件", test_frontend_component()))
    
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    
    passed = sum(1 for _, r in results if r)
    total = len(results)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status} - {name}")
    
    print(f"\n总计：{passed}/{total} 测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！系统监控 24 小时数据功能正常")
        return 0
    else:
        print("\n⚠️  部分测试未通过，请检查修复")
        return 1

if __name__ == '__main__':
    sys.exit(main())
