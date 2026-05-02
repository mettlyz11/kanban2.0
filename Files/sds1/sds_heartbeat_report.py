#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SDS自我驱动系统 - 30分钟周期心跳报告
查询最近30分钟的SDS系统运行数据并生成报告

创建日期: 2026-04-28
"""

import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

# 添加库路径
sys.path.insert(0, str(Path(__file__).parent.parent / 'scripts' / 'lib'))

from db_connector import execute_query

def get_sds_heartbeat_report():
    """生成SDS周期心跳报告"""
    now = datetime.now()
    thirty_minutes_ago = now - timedelta(minutes=30)
    
    print("=" * 60)
    print(f"📊 SDS自我驱动系统 - 周期心跳报告")
    print(f"⏰ 统计周期: {thirty_minutes_ago.strftime('%Y-%m-%d %H:%M:%S')} ~ {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 1. 查询任务生成情况
    print("\n📋 1. 任务生成情况")
    print("-" * 40)
    
    # 查询最近30分钟生成的SDS任务
    generated_tasks = execute_query("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN status = 'blocked' THEN 1 ELSE 0 END) as blocked,
            SUM(CASE WHEN status != 'blocked' THEN 1 ELSE 0 END) as passed
        FROM tasks 
        WHERE created_at >= %s 
          AND (title LIKE '%%SDS%%' OR description LIKE '%%SDS%%')
    """, (thirty_minutes_ago,))
    
    gen_total = generated_tasks[0]['total'] or 0
    gen_blocked = generated_tasks[0]['blocked'] or 0
    gen_passed = generated_tasks[0]['passed'] or 0
    
    print(f"  生成任务总数: {gen_total}")
    print(f"  拦截任务数: {gen_blocked}")
    print(f"  通过审核数: {gen_passed}")
    if gen_total > 0:
        print(f"  通过率: {gen_passed/gen_total*100:.1f}%")
    
    # 2. 查询任务执行情况
    print("\n🔧 2. 任务执行与验证情况")
    print("-" * 40)
    
    executed_tasks = execute_query("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
            SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
            SUM(CASE WHEN status = 'in_progress' THEN 1 ELSE 0 END) as in_progress,
            SUM(CASE WHEN sds_verified = 1 THEN 1 ELSE 0 END) as verified
        FROM tasks 
        WHERE updated_at >= %s
          AND (title LIKE '%%SDS%%' OR description LIKE '%%SDS%%')
    """, (thirty_minutes_ago,))
    
    exec_total = executed_tasks[0]['total'] or 0
    exec_completed = executed_tasks[0]['completed'] or 0
    exec_failed = executed_tasks[0]['failed'] or 0
    exec_in_progress = executed_tasks[0]['in_progress'] or 0
    exec_verified = executed_tasks[0]['verified'] or 0
    
    print(f"  分发执行任务数: {exec_total}")
    print(f"  完成数: {exec_completed}")
    print(f"  验证通过数: {exec_verified}")
    print(f"  失败数: {exec_failed}")
    print(f"  进行中: {exec_in_progress}")
    
    # 3. 项目缺口引擎运行情况
    print("\n🎯 3. 项目缺口引擎运行情况")
    print("-" * 40)
    
    gap_analysis = execute_query("""
        SELECT 
            COUNT(*) as total_analysis,
            SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
            SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed
        FROM tasks 
        WHERE updated_at >= %s
          AND (title LIKE '%%缺口%%' OR title LIKE '%%gap%%' OR description LIKE '%%缺口%%')
    """, (thirty_minutes_ago,))
    
    gap_total = gap_analysis[0]['total_analysis'] or 0
    gap_completed = gap_analysis[0]['completed'] or 0
    gap_failed = gap_analysis[0]['failed'] or 0
    
    print(f"  缺口分析任务数: {gap_total}")
    print(f"  完成数: {gap_completed}")
    print(f"  失败数: {gap_failed}")
    
    # 查询最近的缺口分析任务详情
    recent_gaps = execute_query("""
        SELECT id, title, status, created_at
        FROM tasks 
        WHERE (title LIKE '%%缺口%%' OR title LIKE '%%gap%%' OR description LIKE '%%缺口%%')
        ORDER BY created_at DESC
        LIMIT 3
    """)
    
    if recent_gaps:
        print(f"\n  最近缺口任务:")
        for gap in recent_gaps:
            print(f"    - [{gap['id']}] {gap['title']} ({gap['status']})")
    
    # 4. 系统整体健康状态评估
    print("\n💚 4. 系统整体健康状态评估")
    print("-" * 40)
    
    # 计算健康分数
    health_score = 100
    
    # 扣分规则
    if gen_blocked > gen_total * 0.5:
        health_score -= 20
    if exec_failed > exec_total * 0.2 and exec_total > 0:
        health_score -= 20
    if gap_failed > 0:
        health_score -= 10
    
    # 活跃度检测
    if gen_total == 0 and exec_total == 0:
        health_score -= 30
        print("  ⚠️ 警告: 本周期内系统无活动记录")
    
    # 健康状态判定
    if health_score >= 80:
        status = "🟢 健康"
        status_desc = "系统运行正常，任务生成和执行稳定"
    elif health_score >= 60:
        status = "🟡 良好"
        status_desc = "系统基本正常，存在少量异常"
    elif health_score >= 40:
        status = "🟠 警告"
        status_desc = "系统存在较多异常，需要关注"
    else:
        status = "🔴 异常"
        status_desc = "系统运行异常，需要立即检查"
    
    print(f"  健康分数: {health_score}/100")
    print(f"  健康状态: {status}")
    print(f"  状态说明: {status_desc}")
    
    # 5. 异常与建议
    print("\n⚠️ 5. 异常问题与建议")
    print("-" * 40)
    
    issues = []
    
    if gen_total == 0 and exec_total == 0:
        issues.append("❌ 系统活跃度异常: 30分钟内无SDS任务活动")
        issues.append("   建议: 检查SDS主进程是否正常运行，查看 task_generation_guard 状态")
    
    if gen_blocked > 0:
        issues.append(f"⚠️  任务拦截: 有 {gen_blocked} 个任务被生成守卫拦截")
        issues.append("   建议: 查看被拦截任务，评估拦截规则是否合理")
    
    if exec_failed > 0:
        issues.append(f"❌ 执行失败: 有 {exec_failed} 个任务执行失败")
        issues.append("   建议: 检查失败任务详情，分析错误原因")
    
    if gap_failed > 0:
        issues.append(f"⚠️  缺口引擎异常: 有 {gap_failed} 个缺口分析任务失败")
        issues.append("   建议: 检查 project_gap_analyzer.py 模块运行状态")
    
    if issues:
        for issue in issues:
            print(f"  {issue}")
    else:
        print("  ✅ 本周期无异常问题")
    
    # 6. 总结
    print("\n" + "=" * 60)
    print("📝 总结")
    print("=" * 60)
    
    if health_score >= 80:
        print("  ✅ SDS自我驱动系统运行状态良好")
        print("     - 任务生成机制正常")
        print("     - 任务执行成功率高")
        print("     - 项目缺口引擎运行稳定")
    elif health_score >= 60:
        print("  ⚠️ SDS系统基本正常，建议关注少量异常")
    else:
        print("  🚨 SDS系统存在异常，建议及时检查处理")
    
    print("=" * 60)
    print(f"📅 报告生成时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == '__main__':
    try:
        get_sds_heartbeat_report()
    except Exception as e:
        print(f"❌ 生成报告失败: {e}")
        sys.exit(1)
