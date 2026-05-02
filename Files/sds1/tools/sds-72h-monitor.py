#!/usr/bin/env python3
"""
SDS 72h Unattended Test Monitor
- 每5分钟检查SDS全组件健康状态
- 异常自动检测 + 自愈
- 72h无人值守验证报告
- 告警通知

版本: v1.0 | 2026-04-20
"""

import pymysql
from lib.db_connector import get_db_connection
import subprocess
import json
import os
import time
from datetime import datetime, timedelta

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
MONITOR_LOG = f'{LOG_DIR}/72h-monitor.log'
HEALTH_REPORT = f'{LOG_DIR}/72h-health.json'
ALERT_LOG = f'{LOG_DIR}/alerts.json'

# 72h 验证目标
TARGET_HOURS = 72
MIN_AUTO_TASKS = 5

# 告警阈值
HB_WARN = 30
HB_TIMEOUT = 60
MAX_FAIL_RATE = 0.15

# 自愈
SELF_HEAL = True
MAX_RESTARTS = 3

# ===== 状态 =====
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
    with open(MONITOR_LOG, 'a') as f:
        f.write(line + '\n')

def get_db():
    global conn
    try:
        if conn:
            conn.ping(reconnect=True)
            return conn
    except: pass
    for i in range(3):
        try:
            conn = get_db_connection()
            return conn
        except Exception as e:
            log(f"DB连接失败({i+1}/3): {e}", 'ERROR')
            if i < 2: time.sleep(5)
    return None

def send_alert(category, message, severity='warning'):
    a = {'time': datetime.now().isoformat(), 'cat': category, 'msg': message, 'sev': severity}
    alerts.append(a)
    log(f"🚨 [{severity.upper()}] {category}: {message}", 'ALERT')
    try:
        with open(ALERT_LOG, 'w') as f:
            json.dump(alerts[-50:], f, ensure_ascii=False, indent=2)
    except: pass

# ===== 检查项 =====

def check_sched_proc():
    try:
        r = subprocess.run(['pgrep', '-f', 'self-driving-scheduler-v4.3.py'],
                          capture_output=True, text=True, timeout=5)
        pids = [p for p in r.stdout.strip().split('\n') if p]
        return (len(pids) > 0, f"PID={','.join(pids)}" if pids else "未运行")
    except Exception as e:
        return (False, str(e))

def check_sched_log():
    try:
        lf = '/Users/mettlyz/.openclaw/logs/scheduler/scheduler-v4.3-stdout.log'
        if not os.path.exists(lf): return (False, "无日志")
        age = (time.time() - os.path.getmtime(lf)) / 60
        return (age < 15, f"{age:.0f}min前更新")
    except Exception as e:
        return (False, str(e))

def check_db():
    db = get_db()
    if not db: return (False, "连接失败")
    try:
        with db.cursor() as c:
            c.execute("SELECT 1")
            c.execute("SELECT COUNT(*) c FROM tasks WHERE status='pending'")
            p = c.fetchone()['c']
            c.execute("SELECT COUNT(*) c FROM tasks WHERE status='in_progress'")
            i = c.fetchone()['c']
        return (True, f"正常(pending={p}, running={i})")
    except Exception as e:
        return (False, str(e))

def check_heartbeats():
    db = get_db()
    if not db: return (False, "DB不可用", [])
    with db.cursor() as c:
        c.execute("""SELECT id, title, last_heartbeat,
            TIMESTAMPDIFF(MINUTE, last_heartbeat, NOW()) age
            FROM tasks WHERE status='in_progress' AND last_heartbeat IS NOT NULL
            ORDER BY age DESC""")
        tasks = c.fetchall()
    issues = []
    for t in tasks:
        if t['age'] >= HB_TIMEOUT:
            issues.append(f"#{t['id']}超时{t['age']}min")
        elif t['age'] >= HB_WARN:
            issues.append(f"#{t['id']}警告{t['age']}min")
    return (len(issues) == 0, f"{len(tasks)}个正常" if not issues else f"{len(issues)}异常", issues)

def check_quality():
    db = get_db()
    if not db: return (False, "DB不可用", {})
    with db.cursor() as c:
        c.execute("""SELECT COUNT(*) total,
            SUM(CASE WHEN (execution_log IS NULL OR execution_log='' OR CHAR_LENGTH(execution_log)<200) THEN 1 ELSE 0 END) bad_log,
            SUM(CASE WHEN (task_summary IS NULL OR task_summary='' OR CHAR_LENGTH(task_summary)<50) THEN 1 ELSE 0 END) bad_sum,
            SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END) failed
            FROM tasks WHERE task_type LIKE 'auto_generated%'""")
        s = c.fetchone()
    total = s['total'] or 0
    if total == 0: return (True, "无数据", s)
    fr = s['failed'] / total
    s['fr'] = round(fr * 100, 1)
    return (fr < MAX_FAIL_RATE, f"失败率{fr*100:.0f}%", s)

def check_taskgen():
    db = get_db()
    if not db: return (False, "DB不可用", {})
    with db.cursor() as c:
        c.execute("""SELECT COUNT(*) total,
            SUM(CASE WHEN created_at > NOW()-INTERVAL 1 HOUR THEN 1 ELSE 0 END) h1,
            SUM(CASE WHEN created_at > NOW()-INTERVAL 24 HOUR THEN 1 ELSE 0 END) h24,
            SUM(CASE WHEN status='completed' AND created_at > NOW()-INTERVAL 24 HOUR THEN 1 ELSE 0 END) done24
            FROM tasks WHERE task_type LIKE 'auto_generated%'""")
        s = c.fetchone()
    elapsed = (datetime.now() - start_time).total_seconds() / 3600 if start_time else 0
    s['elapsed'] = round(elapsed, 1)
    s['progress'] = round(min(elapsed / TARGET_HOURS * 100, 100), 1)
    return (True, f"总计{s['total']} 24h={s['h24']}", s)

def check_watchdog():
    try:
        r = subprocess.run(['launchctl', 'list'], capture_output=True, text=True, timeout=5)
        return ('scheduler-watchdog' in r.stdout, "运行中" if 'scheduler-watchdog' in r.stdout else "未注册")
    except: return (False, "检查失败")

# ===== 自愈 =====

def heal_sched():
    global restart_count
    if restart_count >= MAX_RESTARTS:
        log(f"⛔ 已达最大重启次数({MAX_RESTARTS})", 'CRITICAL')
        send_alert('MAX_RESTARTS', f"已达{MAX_RESTARTS}次", 'critical')
        return False
    log(f"🔧 自愈: 重启调度器({restart_count+1}/{MAX_RESTARTS})", 'WARN')
    try:
        subprocess.run(['pkill', '-f', 'self-driving-scheduler-v4.3.py'], timeout=5)
        time.sleep(3)
        r = subprocess.run(['launchctl', 'kickstart', 'com.openclaw.scheduler-v4.3'],
                          capture_output=True, text=True, timeout=10)
        if r.returncode == 0:
            restart_count += 1
            log(f"✅ 重启成功(#{restart_count})")
            send_alert('RESTART', f"自动重启#{restart_count}", 'info')
            return True
        log(f"❌ 重启失败: {r.stderr[:200]}", 'ERROR')
        return False
    except Exception as e:
        log(f"❌ 自愈异常: {e}", 'ERROR')
        return False

def heal_stale():
    db = get_db()
    if not db: return 0
    n = 0
    with db.cursor() as c:
        c.execute("""SELECT id FROM tasks WHERE status='in_progress'
            AND last_heartbeat IS NOT NULL
            AND TIMESTAMPDIFF(MINUTE, last_heartbeat, NOW()) > %s""", (HB_TIMEOUT,))
        for t in c.fetchall():
            log(f"🔧 #{t['id']}心跳超时→pending", 'WARN')
            c.execute("UPDATE tasks SET status='pending',task_summary=CONCAT(IFNULL(task_summary,''),'[自愈:心跳超时]'),updated_at=NOW() WHERE id=%s", (t['id'],))
            conn.commit()
            n += 1
        c.execute("""SELECT id FROM tasks WHERE status='in_progress' AND last_heartbeat IS NULL
            AND updated_at < NOW()-INTERVAL 30 MINUTE""")
        for t in c.fetchall():
            log(f"🔧 #{t['id']}无心跳→pending", 'WARN')
            c.execute("UPDATE tasks SET status='pending',task_summary=CONCAT(IFNULL(task_summary,''),'[自愈:僵尸]'),updated_at=NOW() WHERE id=%s", (t['id'],))
            conn.commit()
            n += 1
    if n: log(f"✅ 自愈恢复{n}个")
    return n

# ===== 报告 =====

def gen_report():
    elapsed = (datetime.now() - start_time).total_seconds() / 3600 if start_time else 0
    checks = {
        'sched_proc': check_sched_proc(),
        'sched_log': check_sched_log(),
        'db': check_db(),
        'heartbeats': check_heartbeats()[:2],
        'quality': check_quality()[:2],
        'taskgen': check_taskgen()[:2],
        'watchdog': check_watchdog(),
    }
    ok = all(c[0] for c in checks.values())
    report = {
        'ts': datetime.now().isoformat(),
        'uptime_h': round(elapsed, 2),
        'target_h': TARGET_HOURS,
        'progress': round(min(elapsed / TARGET_HOURS * 100, 100), 1),
        'restarts': restart_count,
        'alerts': len(alerts),
        'ok': ok,
        'checks': {k: {'ok': v[0], 'msg': v[1]} for k, v in checks.items()},
    }
    snapshots.append({'ts': datetime.now().isoformat(), 'up': round(elapsed, 2), 'ok': ok})
    try:
        with open(HEALTH_REPORT, 'w') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log(f"保存报告失败: {e}", 'ERROR')
    return report

def print_report(r):
    s = "✅ HEALTHY" if r['ok'] else "⚠️ DEGRADED"
    log(f"\n{'='*60}")
    log(f"📊 SDS Health | {r['uptime_h']:.1f}h/{TARGET_HOURS}h ({r['progress']:.0f}%) | {s}")
    log(f"{'='*60}")
    for n, c in r['checks'].items():
        log(f"  {'✅' if c['ok'] else '❌'} {n}: {c['msg']}")
    log(f"  🔄重启:{r['restarts']}次 🚨告警:{r['alerts']}条 快照:{len(snapshots)}个")

# ===== 主循环 =====

def run_cycle():
    issues = []
    # 1. 进程
    ok, msg = check_sched_proc()
    if not ok:
        issues.append('sched_down')
        send_alert('SCHED_DOWN', msg, 'critical')
        if SELF_HEAL:
            time.sleep(2)
            heal_sched()
            ok, msg = check_sched_proc()
            if not ok:
                send_alert('RESTART_FAIL', '调度器重启失败', 'critical')
    # 2. 日志
    ok, msg = check_sched_log()
    if not ok:
        issues.append('log_stale')
        send_alert('LOG_STALE', msg, 'warning')
    # 3. DB
    ok, msg = check_db()
    if not ok:
        issues.append('db_down')
        send_alert('DB_DOWN', msg, 'critical')
        return issues
    # 4. 心跳
    ok, msg, hb_issues = check_heartbeats()
    if not ok:
        for i in hb_issues:
            send_alert('HB', i, 'warning')
        issues.append('heartbeats')
    # 5. 质量
    ok, msg, qs = check_quality()
    if not ok:
        issues.append('quality')
        send_alert('QUALITY', msg, 'warning')
    # 6. 任务生成
    ok, msg, ts = check_taskgen()
    # 7. Watchdog
    ok, msg = check_watchdog()
    if not ok:
        issues.append('watchdog')
        send_alert('WATCHDOG', msg, 'warning')
    # 自愈
    if SELF_HEAL: heal_stale()
    # 报告
    r = gen_report()
    print_report(r)
    return issues

def main():
    global start_time
    log("🚀 SDS 72h Monitor 启动")
    log(f"目标: {TARGET_HOURS}h | 间隔: {CHECK_INTERVAL}s | 自愈: {'ON' if SELF_HEAL else 'OFF'}")
    log(f"告警: 心跳>{HB_TIMEOUT}min | 失败率>{MAX_FAIL_RATE*100:.0f}%")
    start_time = datetime.now()

    try:
        n = 0
        while True:
            n += 1
            log(f"\n{'='*60}\n=== 周期 #{n} | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")
            issues = run_cycle()
            if not issues: log("✅ 全部正常")
            else: log(f"⚠️ 问题: {', '.join(issues)}", 'WARN')
            log(f"\n⏰ {CHECK_INTERVAL}s后下次...")
            time.sleep(CHECK_INTERVAL)
    except KeyboardInterrupt:
        log("\n👋 手动停止")
        r = gen_report()
        print_report(r)
        log(f"\n📊 最终: {r['uptime_h']}h | 重启{restart_count}次 | 告警{len(alerts)}条 | 快照{len(snapshots)}个")

if __name__ == '__main__':
    main()
