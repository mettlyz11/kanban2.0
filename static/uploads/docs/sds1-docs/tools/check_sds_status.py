#!/usr/bin/env python3
"""
SDS 系统状态检查
检查自我驱动系统的运行状态、任务生成、监控机制
"""

import os
import sys
sys.path.insert(0, 'os.path.expanduser("~/.openclaw/workspace")/scripts')
from lib.db_connector import get_db_connection, execute_query
from datetime import datetime, timedelta

def print_section(title):
    # print(f"\n{'='*60}")
    # print(f"  {title}")
    # print(f"{'='*60}\n")

def check_database_connection():
    """检查数据库连接"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT VERSION()")
        version = cursor.fetchone()
        # print(f"✅ 数据库连接成功")
        # print(f"   MySQL 版本: {version[0]}")
        return True, conn
    except Exception as e:
        # print(f"❌ 数据库连接失败: {e}")
        return False, None

def check_task_stats(conn):
    """检查任务统计"""
    cursor = conn.cursor()
    
    # 按状态统计
    cursor.execute("""
        SELECT status, COUNT(*) as count
        FROM tasks
        GROUP BY status
        ORDER BY status
    """)
    results = cursor.fetchall()
    
    # print("📊 任务状态统计:")
    for status, count in results:
        # print(f"   {status}: {count}")
    
    # 统计24小时内创建的任务
    cursor.execute("""
        SELECT COUNT(*) FROM tasks
        WHERE created_at > DATE_SUB(NOW(), INTERVAL 24 HOUR)
    """)
    count_24h = cursor.fetchone()[0]
    # print(f"\n   过去24小时创建: {count_24h} 个任务")
    
    # 统计最近完成的任务
    cursor.execute("""
        SELECT COUNT(*) FROM tasks
        WHERE updated_at > DATE_SUB(NOW(), INTERVAL 24 HOUR)
          AND status = 'completed'
    """)
    completed_24h = cursor.fetchone()[0]
    # print(f"   过去24小时完成: {completed_24h} 个任务")

def check_in_progress_tasks(conn):
    """检查进行中的任务"""
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT id, title, status, created_at, updated_at,
               TIMESTAMPDIFF(MINUTE, updated_at, NOW()) as minutes_since_update
        FROM tasks
        WHERE status = 'in_progress'
        ORDER BY updated_at ASC
    """)
    tasks = cursor.fetchall()
    
    # print(f"\n🔄 进行中的任务 ({len(tasks)} 个):")
    for t in tasks:
        heartbeat_status = "✅"
        if t['minutes_since_update'] > 30:
            heartbeat_status = "⚠️ >30分钟"
        if t['minutes_since_update'] > 60:
            heartbeat_status = "🔴 >60分钟"
        # print(f"   #{t['id']}: {t['title'][:50]}... - 最后更新: {t['minutes_since_update']} 分钟前 {heartbeat_status}")

def check_pending_tasks(conn):
    """检查待处理任务"""
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT id, title, priority, created_at, category_id
        FROM tasks
        WHERE status = 'pending'
          AND requires_audit = 0
        ORDER BY priority DESC, created_at DESC
        LIMIT 10
    """)
    tasks = cursor.fetchall()
    
    # print(f"\n📋 待处理任务 (Top 10):")
    for t in tasks:
        # print(f"   #{t['id']} [{t['priority']}]: {t['title'][:60]}...")

def check_sds_logs():
    """检查SDS日志"""
    log_files = [
        '/Users/mettlyz/.openclaw/logs/v4-scheduler.log',
        '/Users/mettlyz/.openclaw/logs/self-driving.log',
        '/Users/mettlyz/.openclaw/logs/scheduler-watchdog.log',
    ]
    
    # print("\n📝 日志文件状态:")
    for log_file in log_files:
        if os.path.exists(log_file):
            size_mb = os.path.getsize(log_file) / 1024 / 1024
            mtime = datetime.fromtimestamp(os.path.getmtime(log_file))
            age = (datetime.now() - mtime).total_seconds() / 60
            # print(f"   {os.path.basename(log_file)}: {size_mb:.2f} MB, 最后更新: {age:.1f} 分钟前")
        else:
            # print(f"   {os.path.basename(log_file)}: ❌ 不存在")

def check_scheduler_process():
    """检查调度器进程"""
    import subprocess
    result = subprocess.run(
        ['pgrep', '-f', 'self-driving-scheduler'],
        capture_output=True, text=True
    )
    
    pids = result.stdout.strip().split('\n')
    if pids and pids[0]:
        # print(f"\n🚀 调度器进程: {len(pids)} 个运行中")
        for pid in pids:
            # print(f"   PID: {pid}")
    else:
        # print(f"\n⚠️ 调度器进程: 未运行")

def main():
    print_section("自我驱动系统 (SDS) v4.3 状态检查")
    # print(f"检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # 1. 检查数据库连接
    db_ok, conn = check_database_connection()
    if not db_ok:
        return
    
    # 2. 检查任务统计
    check_task_stats(conn)
    
    # 3. 检查进行中的任务
    check_in_progress_tasks(conn)
    
    # 4. 检查待处理任务
    check_pending_tasks(conn)
    
    # 5. 检查日志
    check_sds_logs()
    
    # 6. 检查进程
    check_scheduler_process()
    
    # 7. 组件完整性检查
    print_section("SDS 核心组件检查")
    
    components = [
        ('self-driving-scheduler-v4.3.py', '核心调度器'),
        ('kanban_task_manager.py', '看板管理模块'),
        ('task_verifier.py', '任务验证器'),
        ('task_wrapper.py', '任务包装器'),
        ('scheduler-watchdog.py', '监控自愈模块'),
        ('smart-task-scheduler.py', '智能任务生成器'),
    ]
    
    for filename, description in components:
        path = f'os.path.expanduser("~/.openclaw/workspace")/scripts/{filename}'
        if os.path.exists(path):
            size = os.path.getsize(path)
            # print(f"✅ {description} ({filename}): {size} 字节")
        else:
            # print(f"❌ {description} ({filename}): 缺失")
    
    conn.close()
    
    print_section("检查完成")

if __name__ == '__main__':
    main()
