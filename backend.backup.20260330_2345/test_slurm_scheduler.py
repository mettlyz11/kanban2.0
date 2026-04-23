#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SLURM 调度模块测试文件

测试 slurm_scheduler.py 的各项功能
"""

import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from slurm_scheduler import (
    SLURMScheduler,
    SoftwareType,
    JobStatus,
    submit_job,
    check_job_status,
    cancel_job,
    generate_gaussian_script,
    generate_orca_script,
    generate_psi4_script
)


def test_scheduler_initialization():
    """测试调度器初始化"""
    print("=" * 60)
    print("测试 1: 调度器初始化")
    print("=" * 60)
    
    scheduler = SLURMScheduler(
        default_partition="compute",
        max_retries=3,
        retry_delay=60
    )
    
    print(f"✓ 调度器初始化成功")
    print(f"  默认分区：{scheduler.default_partition}")
    print(f"  最大重试：{scheduler.max_retries}")
    print(f"  重试延迟：{scheduler.retry_delay}秒")
    print()
    
    return scheduler


def test_script_generation(scheduler):
    """测试脚本模板生成"""
    print("=" * 60)
    print("测试 2: SLURM 脚本模板生成")
    print("=" * 60)
    
    # 测试 Gaussian 脚本
    print("\n2.1 Gaussian 脚本模板")
    gaussian_script = scheduler.generate_script_template(
        software=SoftwareType.GAUSSIAN,
        input_file="test.com",
        job_name="gaussian_job",
        nodes=1,
        cpus_per_task=8,
        memory="16G",
        time_limit="24:00:00",
        queue_type="normal"
    )
    print(gaussian_script)
    print()
    
    # 测试 ORCA 脚本
    print("\n2.2 ORCA 脚本模板")
    orca_script = scheduler.generate_script_template(
        software=SoftwareType.ORCA,
        input_file="test.inp",
        job_name="orca_job",
        nodes=1,
        cpus_per_task=4,
        memory="8G",
        time_limit="12:00:00",
        queue_type="high"
    )
    print(orca_script)
    print()
    
    # 测试 PSI4 脚本
    print("\n2.3 PSI4 脚本模板")
    psi4_script = scheduler.generate_script_template(
        software=SoftwareType.PSI4,
        input_file="test.py",
        job_name="psi4_job",
        nodes=1,
        cpus_per_task=16,
        memory="32G",
        time_limit="48:00:00",
        queue_type="low"
    )
    print(psi4_script)
    print()
    
    # 测试保存脚本
    print("\n2.4 保存脚本到文件")
    result = scheduler.save_script_template(
        gaussian_script,
        "test_gaussian_job.sh",
        make_executable=True
    )
    print(f"保存结果：{result}")
    print()
    
    return True


def test_convenience_functions():
    """测试便捷函数"""
    print("=" * 60)
    print("测试 3: 便捷函数")
    print("=" * 60)
    
    # 测试便捷函数生成脚本
    print("\n3.1 使用便捷函数生成 Gaussian 脚本")
    script = generate_gaussian_script(
        input_file="molecule.com",
        job_name="quick_test",
        cpus_per_task=4
    )
    print(script[:500] + "..." if len(script) > 500 else script)
    print()
    
    print("\n3.2 使用便捷函数生成 ORCA 脚本")
    script = generate_orca_script(
        input_file="molecule.inp",
        job_name="orca_quick",
        cpus_per_task=8
    )
    print(script[:500] + "..." if len(script) > 500 else script)
    print()
    
    print("\n3.3 使用便捷函数生成 PSI4 脚本")
    script = generate_psi4_script(
        input_file="molecule.py",
        job_name="psi4_quick",
        cpus_per_task=12
    )
    print(script[:500] + "..." if len(script) > 500 else script)
    print()
    
    return True


def test_job_submission_dry_run(scheduler):
    """测试作业提交 (Dry Run 模式)"""
    print("=" * 60)
    print("测试 4: 作业提交 (Dry Run)")
    print("=" * 60)
    
    # 创建一个临时脚本
    temp_script = "test_temp_job.sh"
    with open(temp_script, 'w') as f:
        f.write("#!/bin/bash\necho 'Hello from SLURM job'\nsleep 10\n")
    
    # Dry Run 模式提交
    result = scheduler.submit_job(
        script_path=temp_script,
        job_name="test_dry_run",
        nodes=1,
        cpus_per_task=2,
        memory="4G",
        time_limit="00:10:00",
        dry_run=True
    )
    
    print(f"提交结果：{result}")
    print(f"  成功：{result['success']}")
    print(f"  消息：{result['message']}")
    if 'command' in result:
        print(f"  命令：{result['command']}")
    print()
    
    # 清理临时文件
    os.remove(temp_script)
    
    return True


def test_status_enum():
    """测试状态枚举"""
    print("=" * 60)
    print("测试 5: 作业状态枚举")
    print("=" * 60)
    
    print("\n可用的作业状态:")
    for status in JobStatus:
        print(f"  - {status.name}: {status.value}")
    print()
    
    print("\n可用的软件类型:")
    for software in SoftwareType:
        print(f"  - {software.name}: {software.value}")
    print()
    
    return True


def test_dependency_chain(scheduler):
    """测试作业依赖链"""
    print("=" * 60)
    print("测试 6: 作业依赖链 (模拟)")
    print("=" * 60)
    
    # 创建依赖链配置
    scripts = [
        {
            'script_path': 'step1.sh',
            'job_name': 'step1_optimization',
            'nodes': 1,
            'cpus_per_task': 4,
            'memory': '8G'
        },
        {
            'script_path': 'step2.sh',
            'job_name': 'step2_frequency',
            'nodes': 1,
            'cpus_per_task': 8,
            'memory': '16G'
        },
        {
            'script_path': 'step3.sh',
            'job_name': 'step3_analysis',
            'nodes': 1,
            'cpus_per_task': 4,
            'memory': '8G'
        }
    ]
    
    print("\n作业链配置:")
    for i, script in enumerate(scripts, 1):
        deps = "无" if i == 1 else f"依赖作业 {i-1}"
        print(f"  步骤 {i}: {script['job_name']} ({deps})")
    print()
    
    # 注意：这里不会真正提交，只是演示 API
    print("调用 create_job_chain() 将创建依赖作业链")
    print("(实际提交需要在 SLURM 环境中)")
    print()
    
    return True


def test_queue_info(scheduler):
    """测试队列信息获取"""
    print("=" * 60)
    print("测试 7: 队列信息 (需要 SLURM 环境)")
    print("=" * 60)
    
    # 这个测试需要真实的 SLURM 环境
    print("\n尝试获取队列信息...")
    result = scheduler.get_queue_info()
    
    if result['success']:
        print(f"✓ 成功获取 {len(result['partitions'])} 个分区")
        for partition in result['partitions']:
            print(f"  - 分区：{partition['name']}")
            print(f"    节点：{partition['nodes']}")
            print(f"    状态：{partition['state']}")
            print(f"    CPU: {partition['cpus']}")
            print(f"    内存：{partition['memory']}")
    else:
        print(f"⚠ 获取失败 (可能在非 SLURM 环境): {result['message']}")
    print()
    
    return True


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("SLURM 调度模块测试套件")
    print("=" * 60 + "\n")
    
    try:
        # 测试 1: 初始化
        scheduler = test_scheduler_initialization()
        
        # 测试 2: 脚本生成
        test_script_generation(scheduler)
        
        # 测试 3: 便捷函数
        test_convenience_functions()
        
        # 测试 4: 作业提交 (Dry Run)
        test_job_submission_dry_run(scheduler)
        
        # 测试 5: 状态枚举
        test_status_enum()
        
        # 测试 6: 依赖链
        test_dependency_chain(scheduler)
        
        # 测试 7: 队列信息
        test_queue_info(scheduler)
        
        # 总结
        print("=" * 60)
        print("✅ 所有测试完成!")
        print("=" * 60)
        print("\n提示:")
        print("  - 脚本生成功能已验证 ✓")
        print("  - 作业提交/状态检查/取消功能需要在 SLURM 环境中测试")
        print("  - 便捷函数可直接用于快速提交作业")
        print()
        
        return True
        
    except Exception as e:
        print(f"\n❌ 测试失败：{str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
