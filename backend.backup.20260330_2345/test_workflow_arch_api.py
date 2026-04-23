#!/usr/bin/env python3
"""
测试工作流程架构图 API
"""

import requests
import json

BASE_URL = 'http://localhost:5000'

def test_api():
    """测试所有 API 端点"""
    print("🧪 开始测试工作流程架构图 API\n")
    
    # 1. 获取架构图数据
    print("1️⃣ 测试 GET /api/workflow-architecture")
    try:
        response = requests.get(f'{BASE_URL}/api/workflow-architecture')
        result = response.json()
        if result.get('success'):
            print(f"   ✅ 成功获取 {len(result['data']['nodes'])} 个节点，{len(result['data']['connections'])} 个连接")
            print(f"   📊 版本号：{result['data']['version']}")
        else:
            print(f"   ❌ 失败：{result.get('error')}")
    except Exception as e:
        print(f"   ❌ 错误：{e}")
    
    print()
    
    # 2. 同步文件
    print("2️⃣ 测试 POST /api/workflow-architecture/sync")
    try:
        response = requests.post(f'{BASE_URL}/api/workflow-architecture/sync')
        result = response.json()
        if result.get('success'):
            print(f"   ✅ 成功同步 {len(result.get('synced_files', []))} 个文件")
            print(f"   📄 文件：{result.get('synced_files', [])}")
        else:
            print(f"   ❌ 失败：{result.get('error')}")
    except Exception as e:
        print(f"   ❌ 错误：{e}")
    
    print()
    
    # 3. 获取版本历史
    print("3️⃣ 测试 GET /api/workflow-architecture/versions")
    try:
        response = requests.get(f'{BASE_URL}/api/workflow-architecture/versions')
        result = response.json()
        if result.get('success'):
            print(f"   ✅ 共有 {len(result['versions'])} 个版本")
            for ver in result['versions'][:3]:
                print(f"      - 版本 {ver['version']}: {ver['description']}")
        else:
            print(f"   ❌ 失败：{result.get('error')}")
    except Exception as e:
        print(f"   ❌ 错误：{e}")
    
    print()
    
    # 4. 获取文件内容
    print("4️⃣ 测试 GET /api/workflow-architecture/file/SOUL.md")
    try:
        response = requests.get(f'{BASE_URL}/api/workflow-architecture/file/SOUL.md')
        result = response.json()
        if result.get('success'):
            print(f"   ✅ 成功获取文件内容")
            print(f"   📄 标题：{result['data']['title']}")
            print(f"   📝 大小：{result['data']['size']} 字符")
        else:
            print(f"   ❌ 失败：{result.get('error')}")
    except Exception as e:
        print(f"   ❌ 错误：{e}")
    
    print()
    
    # 5. 创建新节点
    print("5️⃣ 测试 POST /api/workflow-architecture/node")
    try:
        response = requests.post(f'{BASE_URL}/api/workflow-architecture/node', json={
            'name': '测试节点',
            'type': 'node',
            'x': 500,
            'y': 500,
            'color': '#ffebee',
            'description': '这是一个测试节点'
        })
        result = response.json()
        if result.get('success'):
            print(f"   ✅ 成功创建节点 ID: {result['node_id']}")
        else:
            print(f"   ❌ 失败：{result.get('error')}")
    except Exception as e:
        print(f"   ❌ 错误：{e}")
    
    print()
    
    # 6. 获取更新后的数据
    print("6️⃣ 再次获取架构图数据（验证节点创建）")
    try:
        response = requests.get(f'{BASE_URL}/api/workflow-architecture')
        result = response.json()
        if result.get('success'):
            print(f"   ✅ 当前共有 {len(result['data']['nodes'])} 个节点")
            # 显示最后 3 个节点
            for node in result['data']['nodes'][-3:]:
                print(f"      - {node['name']} ({node['type']}) @ ({node['x']}, {node['y']})")
        else:
            print(f"   ❌ 失败：{result.get('error')}")
    except Exception as e:
        print(f"   ❌ 错误：{e}")
    
    print()
    print("🎉 API 测试完成！")

if __name__ == '__main__':
    print("=" * 60)
    print("工作流程架构图 API 测试工具")
    print("=" * 60)
    print()
    
    # 检查后端是否运行
    try:
        requests.get(f'{BASE_URL}/', timeout=2)
        print("✅ 后端服务正在运行\n")
        test_api()
    except requests.exceptions.ConnectionError:
        print(f"❌ 无法连接到后端服务 ({BASE_URL})")
        print("💡 请先启动后端：python3 app.py")
    except Exception as e:
        print(f"❌ 错误：{e}")
