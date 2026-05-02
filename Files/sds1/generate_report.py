#!/usr/bin/env python3
import sys
sys.path.insert(0, '/Users/mettlyz/.openclaw/workspace/scripts/lib')
from db_connector import execute_query
from datetime import datetime, timedelta

now = datetime.now()
thirty_ago = now - timedelta(minutes=30)

# 1. 任务生成统计
gen = execute_query("""
    SELECT COUNT(*) as total,
           SUM(CASE WHEN status='blocked' THEN 1 ELSE 0 END) as blocked
    FROM tasks WHERE created_at >= %s 
    AND (title LIKE '%%SDS%%' OR description LIKE '%%SDS%%' OR created_by='sds_system')
""", (thirty_ago,))

# 2. 任务执行统计
exec_stats = execute_query("""
    SELECT COUNT(*) as total,
           SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) as completed,
           SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END) as failed,
           SUM(CASE WHEN status='in_progress' THEN 1 ELSE 0 END) as in_progress
    FROM tasks WHERE updated_at >= %s
    AND (title LIKE '%%SDS%%' OR description LIKE '%%SDS%%' OR created_by='sds_system')
""", (thirty_ago,))

# 3. 缺口引擎统计
gap = execute_query("""
    SELECT COUNT(*) as total,
           SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) as completed,
           SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END) as failed
    FROM tasks WHERE updated_at >= %s
    AND (title LIKE '%%缺口%%' OR title LIKE '%%gap%%' OR description LIKE '%%缺口%%')
""", (thirty_ago,))

# 输出结果
print(f"""
============================================================
📊 SDS自我驱动系统 - 周期心跳报告
⏰ 统计周期: {thirty_ago.strftime('%Y-%m-%d %H:%M:%S')} ~ {now.strftime('%Y-%m-%d %H:%M:%S')}
============================================================

📋 1. 任务生成情况
------------------------------------------------------------
  生成任务总数: {gen[0]['total'] or 0}
  拦截任务数: {gen[0]['blocked'] or 0}
  通过审核数: {(gen[0]['total'] or 0) - (gen[0]['blocked'] or 0)}

🔧 2. 任务执行与验证情况
------------------------------------------------------------
  分发执行任务数: {exec_stats[0]['total'] or 0}
  完成数: {exec_stats[0]['completed'] or 0}
  失败数: {exec_stats[0]['failed'] or 0}
  进行中: {exec_stats[0]['in_progress'] or 0}

🎯 3. 项目缺口引擎运行情况
------------------------------------------------------------
  缺口分析任务数: {gap[0]['total'] or 0}
  完成数: {gap[0]['completed'] or 0}
  失败数: {gap[0]['failed'] or 0}

💚 4. 系统整体健康状态评估
------------------------------------------------------------
  健康分数: 计算中...

⚠️ 5. 异常问题与建议
------------------------------------------------------------
""")

# 计算健康分数
health_score = 100
gen_total = gen[0]['total'] or 0
gen_blocked = gen[0]['blocked'] or 0
exec_total = exec_stats[0]['total'] or 0
exec_failed = exec_stats[0]['failed'] or 0
gap_failed = gap[0]['failed'] or 0

if gen_blocked > gen_total * 0.5 and gen_total > 0:
    health_score -= 20
if exec_failed > exec_total * 0.2 and exec_total > 0:
    health_score -= 20
if gap_failed > 0:
    health_score -= 10
if gen_total == 0 and exec_total == 0:
    health_score -= 30
    print("  ❌ 系统活跃度异常: 30分钟内无SDS任务活动")
    print("     建议: 检查SDS主进程任务生成逻辑")

if health_score >= 80:
    status = "🟢 健康"
elif health_score >= 60:
    status = "🟡 良好"
else:
    status = "🟠 警告" if health_score >= 40 else "🔴 异常"

print(f"  健康分数: {health_score}/100")
print(f"  健康状态: {status}")

print("""
============================================================
📝 总结
============================================================
""")

if health_score >= 80:
    print("  ✅ SDS自我驱动系统运行状态良好")
    print("     - 任务生成机制正常")
    print("     - 任务执行成功率高")
    print("     - 项目缺口引擎运行稳定")
else:
    print("  ⚠️ SDS系统存在异常，建议关注")

print("============================================================")
print(f"📅 报告生成时间: {now.strftime('%Y-%m-%d %H:%M:%S')}")
print("🐕 Dudu - SDS自我驱动系统")
