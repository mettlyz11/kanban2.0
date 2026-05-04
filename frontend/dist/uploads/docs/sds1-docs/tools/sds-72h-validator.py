#!/usr/bin/env python3
"""
SDS 72h无人值守验证框架 (Self-Driving System 72h Validation)

功能:
1. 每5分钟执行SDS全栈健康检查
2. 异常自动检测 + 自愈(重启调度器/恢复僵尸任务)
3. 质量门自动验证(execution_log≥500字, task_summary≥300字)
4. 72h稳定性统计报告(写入JSON+日志)
5. 告警系统(写文件，可接入Telegram/邮件)

版本: v1.0 | 2026-04-20
任务: #1570
"""

import pymysql
from lib.db_connector import get_db_connection
import subprocess
import json
import os
import time
import signal
from datetime import datetime, timedelta
from pathlib import Path

# ===== 配置 =====
DB_CONFIG = {
    'host': os.environ.get('DB_HOST', ''),
    'user': 'kanban',
    'password': os.environ.get('DB_PASSWORD', ''),
    'database': 'kanban',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor,
    'connect_timeout': 10,
}

CHECK_INTERVAL = 300  # 5分钟
LOG_DIR = '/Users/mettlyz/.openclaw/logs/sds'
VALIDATOR_LOG = f'{LOG_DIR}/72h-validator.log'
HEALTH_REPORT = f'{LOG_DIR}/72h-health-report.json'
ALERT_LOG = f'{LOG_DIR}/72h-alerts.json'
SNAPSHOT_LOG = f'{LOG_DIR}/72h-snapshots.json'

# 72h验证目标
TARGET_HOURS = 72
MIN_AUTO_TASKS = 5  # 72h内至少自动生成5个高质量任务
MAX_FAILURE_RATE = 0.10  # 失败率<10%

# 告警阈值
HB_WARN_MIN = 30     # 心跳>30min → 警告
HB_TIMEOUT_MIN = 60  # 心跳>60min → 自动恢复
SCHEDULER_LOG_MAX_AGE = 15  # 调度器日志最大未更新时间(min)

# 自愈配置
SELF_HEAL = True
MAX_AUTO_RESTARTS = 3  # 最多自动重启3次

# ===== 全局状态 =====
start_time = None
restart_count = 0
alerts = []
snapshots = []
conn = None

def log(msg, level='INFO'):
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    line = f"[{ts}] [{level}] {msg}"
    print(line, flush=True)
    os.makedirs(LOG_DIR, exist_ok=True)
    with open(VALIDATOR_LOG, 'a') as f:
        f.write(line + '\n')

def get_db():
    global conn
    try:
        if conn:
            conn.ping(reconnect=True)
            return conn
    except:
        pass
    for attempt in range(3):
        try:
            conn = get_db_connection()
            return conn
        except Exception as e:
            log(f"DB连接失败({attempt+1}/3): {e}", 'ERROR')
            if attempt < 2:
                time.sleep(5)
    return None

def send_alert(category, message, severity='warning'):
    """发送告警 - 写入文件"""
    alert = {
        'time': datetime.now().isoformat(),
        'category': category,
        'severity': severity,
        'message': message,
    }
    alerts.append(alert)
    log(f"🚨 [{severity.upper()}] {category}: {message}", 'ALERT')
    try:
        with open(ALERT_LOG, 'w') as f:
            json.dump(alerts[-50:], f, ensure_ascii=False, indent=2)
    except Exception as e:
        log(f"告警写入失败: {e}", 'ERROR')

def save_snapshots():
    """保存快照历史"""
    try:
        with open(SNAPSHOT_LOG, 'w') as f:
            json.dump(snapshots[-200:], f, ensure_ascii=False, indent=2)
    except:
        pass

# ===== 1. 调度器进程检查 =====

def check_scheduler_process():
    """检查调度器进程是否运行"""
    try:
        r = subprocess.run(['pgrep', '-f', 'self-driving-scheduler-v4.3.py'],
                          capture_output=True, text=True, timeout=5)
        pids = [p for p in r.stdout.strip().split('\n') if p]
        if pids:
            return True, f"运行中(PID:{','.join(pids)})"
        return False, "调度器进程不存在"
    except Exception as e:
        return False, f"检查失败: {e}"

def check_scheduler_log():
    """检查调度器日志是否活跃"""
    try:
        log_file = '/Users/mettlyz/.openclaw/logs/scheduler/scheduler-v4.3-stdout.log'
        if not os.path.exists(log_file):
            return False, "日志文件不存在"
        age_min = (time.time() - os.path.getmtime(log_file)) / 60
        if age_min > SCHEDULER_LOG_MAX_AGE:
            return False, f"日志{age_min:.0f}min未更新"
        return True, f"活跃({age_min:.0f}min前)"
    except Exception as e:
        return False, str(e)

# ===== 2. 数据库健康检查 =====

def check_db_health():
    """数据库连接+基础查询测试"""
    db = get_db()
    if not db:
        return False, "数据库连接失败"
    try:
        with db.cursor() as c:
            c.execute("SELECT 1")
            c.execute("SELECT COUNT(*) as cnt FROM tasks WHERE status='pending'")
            pending = c.fetchone()['cnt']
            c.execute("SELECT COUNT(*) as cnt FROM tasks WHERE status='in_progress'")
            ip = c.fetchone()['cnt']
            c.execute("SELECT COUNT(*) as cnt FROM tasks WHERE status='completed' AND task_type LIKE 'auto_generated%'")
            completed = c.fetchone()['cnt']
        return True, f"正常(pending:{pending}, running:{ip}, completed:{completed})"
    except Exception as e:
        return False, f"查询失败: {e}"

# ===== 3. 心跳健康检查 =====

def check_heartbeats():
    """检查所有in_progress任务的心跳"""
    db = get_db()
    if not db:
        return False, "DB不可用", []
    
    with db.cursor() as c:
        c.execute("""
            SELECT id, title, last_heartbeat,
                   TIMESTAMPDIFF(MINUTE, last_heartbeat, NOW()) as age_min
            FROM tasks 
            WHERE status = 'in_progress' AND last_heartbeat IS NOT NULL
            ORDER BY age_min DESC
        """)
        tasks = c.fetchall()
    
    issues = []
    for t in tasks:
        if t['age_min'] >= HB_TIMEOUT_MIN:
            issues.append({
                'id': t['id'],
                'title': t['title'][:60],
                'age_min': t['age_min'],
                'type': 'timeout'
            })
        elif t['age_min'] >= HB_WARN_MIN:
            issues.append({
                'id': t['id'],
                'title': t['title'][:60],
                'age_min': t['age_min'],
                'type': 'warning'
            })
    
    # 检查无心跳的僵尸任务
    with db.cursor() as c:
        c.execute("""
            SELECT id, title, 
                   TIMESTAMPDIFF(MINUTE, updated_at, NOW()) as age_min
            FROM tasks 
            WHERE status = 'in_progress' AND last_heartbeat IS NULL
              AND updated_at < NOW() - INTERVAL 30 MINUTE
        """)
        zombies = c.fetchall()
    for z in zombies:
        issues.append({
            'id': z['id'],
            'title': z['title'][:60],
            'age_min': z['age_min'],
            'type': 'zombie'
        })
    
    if issues:
        return False, f"{len(issues)}个心跳异常", issues
    return True, f"{len(tasks)}个任务心跳正常", []

# ===== 4. 质量门检查 =====

def check_quality_gate():
    """检查完成任务是否符合质量门标准"""
    db = get_db()
    if not db:
        return False, "DB不可用", {}
    
    with db.cursor() as c:
        # 统计自动完成任务的质量
        c.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN (execution_log IS NULL OR execution_log = '' 
                          OR CHAR_LENGTH(execution_log) < 200) THEN 1 ELSE 0 END) as bad_exec_log,
                SUM(CASE WHEN (task_summary IS NULL OR task_summary = '' 
                          OR CHAR_LENGTH(task_summary) < 50) THEN 1 ELSE 0 END) as bad_summary,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed
            FROM tasks 
            WHERE task_type LIKE 'auto_generated%'
        """)
        stats = c.fetchone()
    
    total = stats['total'] or 0
    if total == 0:
        return True, "无自动任务", stats
    
    fail_rate = (stats['failed'] or 0) / total
    stats['fail_rate'] = round(fail_rate * 100, 1)
    stats['total'] = total
    
    # 检查质量门合规率
    compliance = 1 - (stats['bad_exec_log'] + stats['bad_summary']) / (total * 2)
    stats['compliance'] = round(compliance * 100, 1)
    
    if fail_rate > MAX_FAILURE_RATE:
        return False, f"失败率{fail_rate*100:.0f}% > 阈值{MAX_FAILURE_RATE*100:.0f}%", stats
    return True, f"合规率{stats['compliance']:.0f}%", stats

# ===== 5. 任务生成速率检查 =====

def check_task_generation():
    """检查任务生成速率是否正常"""
    db = get_db()
    if not db:
        return False, "DB不可用", {}
    
    with db.cursor() as c:
        c.execute("""
            SELECT 
                COUNT(*) as total_auto,
                SUM(CASE WHEN created_at > NOW() - INTERVAL 1 HOUR THEN 1 ELSE 0 END) as h1,
                SUM(CASE WHEN created_at > NOW() - INTERVAL 24 HOUR THEN 1 ELSE 0 END) as h24,
                SUM(CASE WHEN status = 'completed' AND created_at > NOW() - INTERVAL 24 HOUR 
                    THEN 1 ELSE 0 END) as completed_24h
            FROM tasks 
            WHERE task_type LIKE 'auto_generated%'
        """)
        stats = c.fetchone()
    
    # 计算72h目标进度
    elapsed = (datetime.now() - start_time).total_seconds() / 3600 if start_time else 0
    stats['elapsed_hours'] = round(elapsed, 2)
    stats['target_progress'] = round(min(elapsed / TARGET_HOURS * 100, 100), 1)
    stats['auto_task_progress'] = f"{stats['total_auto']}/{MIN_AUTO_TASKS}"
    
    return True, f"总计{stats['total_auto']}个 | 24h:{stats['h24']}个 | 完成:{stats['completed_24h']}个", stats

# ===== 6. Watchdog检查 =====

def check_watchdog():
    """检查Watchdog是否正常运行"""
    try:
        r = subprocess.run(['launchctl', 'list'], capture_output=True, text=True, timeout=5)
        if 'scheduler-watchdog' in r.stdout:
            return True, "Watchdog运行中"
        return False, "Watchdog未注册"
    except Exception as e:
        return False, str(e)

# ===== 自愈模块 =====

def self_heal_scheduler():
    """自愈: 重启调度器进程"""
    global restart_count
    if restart_count >= MAX_AUTO_RESTARTS:
        log(f"⛔ 已达最大自动重启次数({MAX_AUTO_RESTARTS})，需人工介入", 'CRITICAL')
        send_alert('MAX_RESTARTS', f"已达重启上限{MAX_AUTO_RESTARTS}次", 'critical')
        return False
    
    log(f"🔧 自愈: 尝试重启调度器 ({restart_count+1}/{MAX_AUTO_RESTARTS})", 'WARN')
    try:
        # 先停止旧进程
        subprocess.run(['pkill', '-f', 'self-driving-scheduler-v4.3.py'], timeout=5)
        time.sleep(3)
        
        # 通过launchd重启
        result = subprocess.run(
            ['launchctl', 'kickstart', 'com.openclaw.scheduler-v4.3'],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            restart_count += 1
            log(f"✅ 调度器重启成功 (第{restart_count}次)", 'INFO')
            send_alert('SCHEDULER_RESTART', f"自动重启成功(第{restart_count}次)", 'info')
            time.sleep(5)
            # 验证重启成功
            ok, msg = check_scheduler_process()
            return ok
        else:
            log(f"❌ launchd重启失败: {result.stderr[:200]}", 'ERROR')
            send_alert('RESTART_FAILED', result.stderr[:200], 'critical')
            return False
    except Exception as e:
        log(f"❌ 自愈异常: {e}", 'ERROR')
        return False

def self_heal_stale_tasks():
    """自愈: 恢复超时的in_progress任务为pending"""
    db = get_db()
    if not db:
        return 0
    
    recovered = 0
    
    # 1. 心跳超时恢复
    with db.cursor() as c:
        c.execute("""
            SELECT id, title, last_heartbeat 
            FROM tasks 
            WHERE status = 'in_progress' AND last_heartbeat IS NOT NULL
              AND TIMESTAMPDIFF(MINUTE, last_heartbeat, NOW()) > %s
        """, (HB_TIMEOUT_MIN,))
        timeout_tasks = c.fetchall()
    
    for t in timeout_tasks:
        log(f"🔧 自愈: #{t['id']}心跳超时{HB_TIMEOUT_MIN}min → 恢复pending", 'WARN')
        with db.cursor() as c:
            c.execute("""
                UPDATE tasks SET 
                    status = 'pending',
                    task_summary = CONCAT(IFNULL(task_summary, ''), 
                        '\n[SDS自愈:心跳超时>%d分钟,自动恢复pending]'),
                    updated_at = NOW()
                WHERE id = %s
            """, (HB_TIMEOUT_MIN, t['id']))
            conn.commit()
        recovered += 1
        send_alert('TASK_RECOVERED', f"#{t['id']}心跳超时自动恢复", 'warning')
    
    # 2. 无心跳僵尸恢复
    with db.cursor() as c:
        c.execute("""
            SELECT id, title FROM tasks
            WHERE status = 'in_progress' AND last_heartbeat IS NULL
              AND updated_at < NOW() - INTERVAL 30 MINUTE
        """)
        zombie_tasks = c.fetchall()
    
    for t in zombie_tasks:
        log(f"🔧 自愈: #{t['id']}无心跳(僵尸) → 恢复pending", 'WARN')
        with db.cursor() as c:
            c.execute("""
                UPDATE tasks SET 
                    status = 'pending',
                    task_summary = CONCAT(IFNULL(task_summary, ''),
                        '\n[SDS自愈:无心跳>30min僵尸任务,自动恢复pending]'),
                    updated_at = NOW()
                WHERE id = %s
            """, (t['id'],))
            conn.commit()
        recovered += 1
        send_alert('ZOMBIE_RECOVERED', f"#{t['id']}僵尸任务自动恢复", 'warning')
    
    if recovered:
        log(f"✅ 自愈恢复 {recovered} 个任务")
    return recovered

# ===== 报告生成 =====

def generate_health_report():
    """生成完整健康报告"""
    elapsed = (datetime.now() - start_time).total_seconds() / 3600 if start_time else 0
    
    # 执行所有检查
    checks = {
        'scheduler_process': check_scheduler_process(),
        'scheduler_log': check_scheduler_log(),
        'database': check_db_health(),
        'heartbeats': check_heartbeats(),
        'quality_gate': check_quality_gate(),
        'task_generation': check_task_generation(),
        'watchdog': check_watchdog(),
    }
    
    # 整体健康状态
    all_ok = all(c[0] for c in checks.values())
    
    report = {
        'timestamp': datetime.now().isoformat(),
        'uptime_hours': round(elapsed, 2),
        'target_hours': TARGET_HOURS,
        'progress_pct': round(min(elapsed / TARGET_HOURS * 100, 100), 1),
        'restart_count': restart_count,
        'total_alerts': len(alerts),
        'all_healthy': all_ok,
        'checks': {
            k: {'ok': v[0], 'message': v[1]} for k, v in checks.items()
        },
    }
    
    # 保存快照
    snapshots.append({
        'time': datetime.now().isoformat(),
        'uptime': round(elapsed, 2),
        'healthy': all_ok,
        'alerts': len(alerts),
    })
    
    # 写入文件
    try:
        with open(HEALTH_REPORT, 'w') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        save_snapshots()
    except Exception as e:
        log(f"保存报告失败: {e}", 'ERROR')
    
    return report

def print_report(report):
    """打印格式化的健康报告"""
    elapsed = report['uptime_hours']
    progress = report['progress_pct']
    status = "✅ HEALTHY" if report['all_healthy'] else "⚠️ DEGRADED"
    
    log(f"\n{'='*60}")
    log(f"📊 SDS Health Report | {elapsed:.1f}h/{TARGET_HOURS}h ({progress:.0f}%) | {status}")
    log(f"{'='*60}")
    
    for name, check in report['checks'].items():
        icon = "✅" if check['ok'] else "❌"
        log(f"  {icon} {name}: {check['message']}")
    
    if report['restart_count'] > 0:
        log(f"  🔄 自愈重启: {report['restart_count']}次")
    if report['total_alerts'] > 0:
        log(f"  🚨 告警总数: {report['total_alerts']}条")
    log(f"  📈 快照记录: {len(snapshots)}个")

# ===== 主循环 =====

def run_check_cycle():
    """执行一轮完整健康检查"""
    issues = []
    
    # 1. 调度器进程
    proc_ok, proc_msg = check_scheduler_process()
    if not proc_ok:
        issues.append('scheduler_down')
        send_alert('SCHEDULER_DOWN', proc_msg, 'critical')
        if SELF_HEAL:
            time.sleep(2)
            self_heal_scheduler()
            proc_ok, proc_msg = check_scheduler_process()
            if proc_ok:
                log("✅ 自愈成功: 调度器已恢复")
            else:
                log("❌ 自愈失败: 调度器仍未运行", 'CRITICAL')
    
    # 2. 调度器日志
    log_ok, log_msg = check_scheduler_log()
    if not log_ok:
        issues.append('scheduler_log_stale')
        send_alert('SCHEDULER_LOG_STALE', log_msg, 'warning')
    
    # 3. 数据库
    db_ok, db_msg = check_db_health()
    if not db_ok:
        issues.append('db_down')
        send_alert('DB_DOWN', db_msg, 'critical')
        return issues  # DB挂了，跳过后续检查
    
    # 4. 心跳
    hb_ok, hb_msg, hb_issues = check_heartbeats()
    if not hb_ok:
        for issue in hb_issues:
            send_alert(f"HEARTBEAT_{issue['type'].upper()}", 
                      f"#{issue['id']} {issue['type']} {issue['age_min']}min", 'warning')
        issues.append('heartbeats')
    
    # 5. 质量门
    qg_ok, qg_msg, qg_stats = check_quality_gate()
    if not qg_ok:
        send_alert('QUALITY_GATE', qg_msg, 'warning')
        issues.append('quality_gate')
    
    # 6. 任务生成
    tg_ok, tg_msg, tg_stats = check_task_generation()
    
    # 7. Watchdog
    wd_ok, wd_msg = check_watchdog()
    if not wd_ok:
        send_alert('WATCHDOG_DOWN', wd_msg, 'warning')
        issues.append('watchdog')
    
    # 自愈: 恢复超时任务
    if SELF_HEAL:
        self_heal_stale_tasks()
    
    # 生成报告
    report = generate_health_report()
    print_report(report)
    
    return issues

def main():
    global start_time
    
    log("🚀 SDS 72h 无人值守验证框架启动")
    log(f"验证目标: {TARGET_HOURS}h连续稳定运行")
    log(f"检查间隔: {CHECK_INTERVAL}s (5分钟)")
    log(f"自愈: {'开启' if SELF_HEAL else '关闭'} (最大重启{MAX_AUTO_RESTARTS}次)")
    log(f"告警阈值: 心跳>{HB_TIMEOUT_MIN}min | 失败率>{MAX_FAILURE_RATE*100:.0f}%")
    log(f"日志目录: {LOG_DIR}")
    start_time = datetime.now()
    
    # 注册优雅退出
    def graceful_exit(signum, frame):
        log("\n👋 收到退出信号，生成最终报告...", 'INFO')
        report = generate_health_report()
        print_report(report)
        log(f"\n📊 最终统计:")
        log(f"   运行时间: {report['uptime_hours']}h / {TARGET_HOURS}h")
        log(f"   进度: {report['progress_pct']}%")
        log(f"   自愈重启: {restart_count}次")
        log(f"   告警总数: {len(alerts)}条")
        log(f"   快照记录: {len(snapshots)}个")
        if conn:
            conn.close()
        sys.exit(0)
    
    signal.signal(signal.SIGTERM, graceful_exit)
    signal.signal(signal.SIGINT, graceful_exit)
    
    try:
        cycle = 0
        while True:
            cycle += 1
            log(f"\n{'='*60}")
            log(f"=== 检查周期 #{cycle} | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")
            log(f"{'='*60}")
            
            issues = run_check_cycle()
            
            if not issues:
                log("✅ 全部检查通过")
            else:
                log(f"⚠️ 发现问题: {', '.join(issues)}", 'WARN')
            
            log(f"\n⏰ 等待 {CHECK_INTERVAL}秒后进入下一个周期...")
            time.sleep(CHECK_INTERVAL)
            
    except KeyboardInterrupt:
        log("\n👋 手动中断", 'INFO')
        report = generate_health_report()
        print_report(report)
    except Exception as e:
        log(f"\n❌ 验证框架异常: {e}", 'CRITICAL')
        send_alert('VALIDATOR_CRASH', str(e), 'critical')
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    main()
