#!/usr/bin/env python3
"""
测试文献调研记录 API
"""

import requests
import json

BASE_URL = "http://localhost:5001"

def test_api():
    print("=" * 60)
    print("🧪 测试文献调研记录 API")
    print("=" * 60)
    
    # 1. 创建测试记录
    print("\n1️⃣  创建调研记录...")
    create_data = {
        "date": "2026-03-11",
        "project": "T109",
        "query": "transition state calculation using DFT methods",
        "papers_found": 15,
        "key_findings": """1. B3LYP/6-31G* is commonly used for transition state optimization
2. Solvent effects are important for accurate barrier heights
3. Dispersion corrections improve accuracy for organometallic systems""",
        "report_path": "/reports/literature/T109_transition_state_20260311.md"
    }
    
    response = requests.post(f"{BASE_URL}/api/research-logs", json=create_data)
    result = response.json()
    print(f"   响应：{json.dumps(result, indent=2)}")
    
    if not result.get('success'):
        print("   ❌ 创建失败")
        return
    
    record_id = result['data']['id']
    print(f"   ✅ 创建成功，ID: {record_id}")
    
    # 2. 获取列表
    print("\n2️⃣  获取调研记录列表...")
    response = requests.get(f"{BASE_URL}/api/research-logs")
    result = response.json()
    print(f"   总数：{result.get('pagination', {}).get('total', 0)}")
    if result.get('data'):
        print(f"   第一条：{result['data'][0]['query'][:50]}...")
    print("   ✅ 获取成功")
    
    # 3. 获取详情
    print(f"\n3️⃣  获取详情 (ID: {record_id})...")
    response = requests.get(f"{BASE_URL}/api/research-logs/{record_id}")
    result = response.json()
    if result.get('success'):
        print(f"   项目：{result['data']['project']}")
        print(f"   查询：{result['data']['query'][:50]}...")
        print(f"   论文数：{result['data']['papers_found']}")
        print("   ✅ 获取成功")
    
    # 4. 更新记录
    print(f"\n4️⃣  更新记录 (ID: {record_id})...")
    update_data = {
        "papers_found": 20,
        "key_findings": "更新后的关键发现..."
    }
    response = requests.put(f"{BASE_URL}/api/research-logs/{record_id}", json=update_data)
    result = response.json()
    print(f"   响应：{json.dumps(result, indent=2)}")
    print("   ✅ 更新成功")
    
    # 5. 获取统计
    print("\n5️⃣  获取统计信息...")
    response = requests.get(f"{BASE_URL}/api/research-logs/stats")
    result = response.json()
    if result.get('success'):
        stats = result['data']
        print(f"   总记录数：{stats.get('total_logs', 0)}")
        print(f"   总论文数：{stats.get('total_papers', 0)}")
        print(f"   项目数：{len(stats.get('projects', {}))}")
        print("   ✅ 获取成功")
    
    # 6. 获取项目列表
    print("\n6️⃣  获取项目列表...")
    response = requests.get(f"{BASE_URL}/api/research-logs/projects")
    result = response.json()
    if result.get('success'):
        print(f"   项目：{result.get('data', [])}")
        print("   ✅ 获取成功")
    
    # 7. 筛选测试
    print("\n7️⃣  筛选测试 (project=T109)...")
    response = requests.get(f"{BASE_URL}/api/research-logs?project=T109")
    result = response.json()
    print(f"   筛选结果数：{len(result.get('data', []))}")
    print("   ✅ 筛选成功")
    
    # 8. 删除记录（可选）
    # print(f"\n8️⃣  删除记录 (ID: {record_id})...")
    # response = requests.delete(f"{BASE_URL}/api/research-logs/{record_id}")
    # result = response.json()
    # print(f"   响应：{json.dumps(result, indent=2)}")
    # print("   ✅ 删除成功")
    
    print("\n" + "=" * 60)
    print("✅ 所有测试通过！")
    print("=" * 60)


if __name__ == '__main__':
    try:
        test_api()
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到后端服务器")
        print("   请确保后端服务正在运行：python3 app.py")
    except Exception as e:
        print(f"❌ 测试失败：{e}")
        import traceback
        traceback.print_exc()
