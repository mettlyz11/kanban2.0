#!/usr/bin/env python3
import sys
sys.path.insert(0, '/Users/mettlyz/.openclaw/workspace/scripts/lib')
from db_connector import execute_query
from datetime import datetime, timedelta

now = datetime.now()
thirty_ago = now - timedelta(minutes=30)

# 使用正确的转义 - 双百分号表示字面百分号
gen = execute_query("""
    SELECT COUNT(*) as total,
           SUM(CASE WHEN status='blocked' THEN 1 ELSE 0 END) as blocked
    FROM tasks WHERE created_at >= %s 
    AND (title LIKE '%%SDS%%' OR description LIKE '%%SDS%%' OR assignee LIKE '%%sds%%')
""", (thirty_ago,))

exec_stats = execute_query("""
    SELECT COUNT(*) as total,
           SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) as completed,
           SUM(CASE WHEN status LIKE '%%failed%%' THEN 1 ELSE 0 END) as failed,
           SUM(CASE WHEN status='in_progress' THEN 1 ELSE 0 END) as in_progress,
           SUM(CASE WHEN sds_verified = 1 THEN 1 ELSE 0 END) as verified
    FROM tasks WHERE updated_at >= %s
    AND (title LIKE '%%SDS%%' OR description LIKE '%%SDS%%' OR assignee LIKE '%%sds%%')
""", (thirty_ago,))

gap = execute_query("""
    SELECT COUNT(*) as total,
           SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) as completed,
           SUM(CASE WHEN status LIKE '%%failed%%' THEN 1 ELSE 0 END) as failed
    FROM tasks WHERE updated_at >= %s
    AND (title LIKE '%%缺口%%' OR title LIKE '%%gap%%' OR description LIKE '%%缺口%%')
""", (thirty_ago,))

recent_sds = execute_query("""
    SELECT id, title, status, created_at
    FROM tasks 
    WHERE (title LIKE '%%SDS%%' OR description LIKE '%%SDS%%' OR assignee LIKE '%%sds%%')
    ORDER BY created_at DESC
    LIMIT 5
""")

# 输出完整报告
print("=" * 60)
print("📊 SDS自我驱动系统 - 周期心跳报告")
print(f"⏰ 统计周期: {thirty_ago.strftime('%Y-%m-%d %H:%M:%S')} ~ {now.strftime('%Y-%m-%d %H:%M:%S')}")
print("=" * 60)

print("\n📋 1. 任务生成情况")
print("-" * 40)
gen_total = gen[0]['total'] or 0
gen_blocked = gen[0]['blocked'] or 0
gen_passed = gen_total - gen_blocked
print(f"  生成任务总数: {gen_total}")
print(f"  拦截任务数: {gen_blocked}")
print(f"  通过审核数: {gen_passed}")
if gen_total > 0:
    print(f"  通过率: {gen_passed/gen_total*100:.1f}%")

print("\n🔧 2. 任务执行与验证情况")
print("-" * 40)
exec_total = exec_stats[0]['total'] or 0
exec_completed = exec_stats[0]['completed'] or 0
exec_failed = exec_stats[0]['failed'] or 0
exec_in_progress = exec_stats[0]['in_progress'] or 0
exec_verified = exec_stats[0]['verified'] or 0
print(f"  分发执行任务数: {exec_total}")
print(f"  完成数: {exec_completed}")
print(f"  验证通过数: {exec_verified}")
print(f"  失败数: {exec_failed}")
print(f"  进行中: {exec_in_progress}")

print("\n🎯 3. 项目缺口引擎运行情况")
print("-" * 40)
gap_total = gap[0]['total'] or 0
gap_completed = gap[0]['completed'] or 0
gap_failed = gap[0]['failed'] or 0
print(f"  缺口分析任务数: {gap_total}")
print(f"  完成数: {gap_completed}")
print(f"  失败数: {gap_failed}")

if recent_sds:
    print(f"\n  最近SDS任务:")
    for task in recent_sds:
        print(f"    - [{task['id']}] {task['title']} ({task['status']})")

print("\n💚 4. 系统整体健康状态评估")
print("-" * 40)

health_score = 100

if gen_blocked > gen_total * 0.5 and gen_total > 0:
    health_score -= 20
if exec_failed > exec_total * 0.2 and exec_total > 0:
    health_score -= 20
if gap_failed > 0:
    health_score -= 10

if gen_total == 0 and exec_total == 0:
    health_score -= 30

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

print("\n⚠️ 5. 异常问题与建议")
print("-" * 40)

issues = []

import subprocess
ps_result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
sds_running = 'sds_main.py' in ps_result.stdout

if not sds_running:
    issues.append("❌ 主进程异常: SDS主进程未运行")
    issues.append("   建议: 启动 sds_main.py --continuous")

if gen_total == 0 and exec_total == 0:
    issues.append("⚠️  系统活跃度低: 30分钟内无SDS任务活动")
    issues.append("   建议: 检查任务生成守卫和调度器状态")

if gen_blocked > 0:
    issues.append(f"⚠️  任务拦截: 有 {gen_blocked} 个任务被生成守卫拦截")
    issues.append("   建议: 查看被拦截任务，评估拦截规则合理性")

if exec_failed > 0:
    issues.append(f"❌ 执行失败: 有 {exec_failed} 个任务执行失败")
    issues.append("   建议: 检查失败任务详情，分析错误原因")

if gap_failed > 0:
    issues.append(f"⚠️  缺口引擎异常: 有 {gap_failed} 个缺口分析任务失败")
    issues.append("   建议: 检查项目缺口分析模块运行状态")

if sds_running:
    issues.insert(0, "✅ SDS主进程运行正常 (PID 检测通过)")

if issues:
    for issue in issues:
        print(f"  {issue}")
else:
    print("  ✅ 本周期无异常问题")

print("\n" + "=" * 60)
print("📝 总结")
print("=" * 60)

if health_score >= 80 and sds_running:
    print("  ✅ SDS自我驱动系统运行状态良好")
    print("     - 主进程运行正常")
    print("     - 任务生成机制正常")
    print("     - 任务执行成功率高")
    print("     - 项目缺口引擎运行稳定")
elif sds_running:
    print("  ⚠️ SDS系统基本正常，建议关注上述异常")
else:
    print("  🚨 SDS主进程未运行，请立即启动！")

print("=" * 60)
print(f"📅 报告生成时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
print("🐕 Dudu - SDS自我驱动系统")
