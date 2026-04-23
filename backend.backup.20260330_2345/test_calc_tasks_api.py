#!/usr/bin/env python3
"""
测试计算任务提交 API
"""
import requests
import json

BASE_URL = "http://localhost:5001/api"

def test_submit_calc_task():
    """测试提交计算任务"""
    print("=" * 60)
    print("测试 1: 提交有效的计算任务")
    print("=" * 60)
    
    # 测试数据
    test_data = {
        "reaction_id": 1,
        "task_type": "optimization",
        "software": "Gaussian",
        "input_data": {
            "method": "B3LYP",
            "basis": "6-31G(d)",
            "molecule": "H2O\nO 0.0 0.0 0.0\nH 0.0 0.757 0.586\nH 0.0 -0.757 0.586"
        }
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/calc-tasks/submit",
            json=test_data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"状态码：{response.status_code}")
        print(f"响应数据：{json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        
        if response.status_code == 201:
            print("✅ 测试通过：任务成功提交")
            return response.json().get('task', {}).get('task_id')
        else:
            print("❌ 测试失败：任务提交失败")
            return None
            
    except Exception as e:
        print(f"❌ 测试异常：{e}")
        return None


def test_submit_missing_fields():
    """测试缺少必需字段"""
    print("\n" + "=" * 60)
    print("测试 2: 缺少必需字段")
    print("=" * 60)
    
    test_data = {
        "reaction_id": 1
        # 缺少 task_type 和 input_data
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/calc-tasks/submit",
            json=test_data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"状态码：{response.status_code}")
        print(f"响应数据：{json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        
        if response.status_code == 400:
            print("✅ 测试通过：正确验证了缺失字段")
        else:
            print("❌ 测试失败：应该返回 400 错误")
            
    except Exception as e:
        print(f"❌ 测试异常：{e}")


def test_invalid_task_type():
    """测试无效的任务类型"""
    print("\n" + "=" * 60)
    print("测试 3: 无效的任务类型")
    print("=" * 60)
    
    test_data = {
        "reaction_id": 1,
        "task_type": "invalid_type",
        "input_data": "test"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/calc-tasks/submit",
            json=test_data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"状态码：{response.status_code}")
        print(f"响应数据：{json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        
        if response.status_code == 400:
            print("✅ 测试通过：正确验证了任务类型")
        else:
            print("❌ 测试失败：应该返回 400 错误")
            
    except Exception as e:
        print(f"❌ 测试异常：{e}")


def test_get_task(task_id):
    """获取任务详情"""
    print("\n" + "=" * 60)
    print(f"测试 4: 获取任务 {task_id} 详情")
    print("=" * 60)
    
    try:
        response = requests.get(f"{BASE_URL}/calc-tasks/{task_id}")
        
        print(f"状态码：{response.status_code}")
        print(f"响应数据：{json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        
        if response.status_code == 200:
            print("✅ 测试通过：成功获取任务详情")
        else:
            print("❌ 测试失败：获取任务失败")
            
    except Exception as e:
        print(f"❌ 测试异常：{e}")


def test_list_tasks():
    """获取任务列表"""
    print("\n" + "=" * 60)
    print("测试 5: 获取任务列表")
    print("=" * 60)
    
    try:
        response = requests.get(f"{BASE_URL}/calc-tasks")
        
        print(f"状态码：{response.status_code}")
        print(f"响应数据：{json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        
        if response.status_code == 200:
            print("✅ 测试通过：成功获取任务列表")
        else:
            print("❌ 测试失败：获取任务列表失败")
            
    except Exception as e:
        print(f"❌ 测试异常：{e}")


def test_get_stats():
    """获取任务统计"""
    print("\n" + "=" * 60)
    print("测试 6: 获取任务统计")
    print("=" * 60)
    
    try:
        response = requests.get(f"{BASE_URL}/calc-tasks/stats")
        
        print(f"状态码：{response.status_code}")
        print(f"响应数据：{json.dumps(response.json(), indent=2, ensure_ascii=False)}")
        
        if response.status_code == 200:
            print("✅ 测试通过：成功获取统计数据")
        else:
            print("❌ 测试失败：获取统计失败")
            
    except Exception as e:
        print(f"❌ 测试异常：{e}")


if __name__ == "__main__":
    print("\n🧪 开始测试计算任务提交 API\n")
    
    # 运行测试
    task_id = test_submit_calc_task()
    test_submit_missing_fields()
    test_invalid_task_type()
    
    if task_id:
        test_get_task(task_id)
    
    test_list_tasks()
    test_get_stats()
    
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)
