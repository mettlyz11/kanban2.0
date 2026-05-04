#!/usr/bin/env python3
"""
Scheduler Watchdog - 僵尸任务检测与清理
每 10 分钟运行一次（通过 launchd 管理）

功能：
1. 查询 in_progress > 30 分钟的任务
2. 检查 sessions_list 是否有对应子代理
3. 无对应子代理 → 标记 failed
4. 记录到 MEMORY.md
"""

import sys
import os
import json
import subprocess
from datetime import datetime

# 添加 kanban_client 到搜索路径
sys.path.insert(0, '/Users/mettlyz/.openclaw/workspace/skills/self-driving-scheduler-skill/execute')
from kanban_client import KanbanClient

LOG_FILE = '/Users/mettlyz/.openclaw/logs/scheduler-watchdog.log'
MEMORY_FILE = '/Users/mettlyz/.openclaw/workspace/MEMORY.md'
ZOMBIE_THRESHOLD_MINUTES = 30


def log(msg):
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    log_line = f"[{ts}] {msg}"
    print(log_line)
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, 'a') as f:
        f.write(log_line + '\n')


def check_subagent_alive(session_key):
    """检查子代理是否还存活"""
    if not session_key or session_key == 'unknown':
        return False

    try:
        result = subprocess.run(
            ['openclaw', 'sessions', 'list', '--json'],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            sessions = json.loads(result.stdout)
            for s in sessions:
                if s.get('sessionKey') == session_key or session_key in s.get('sessionKey', ''):
                    return True
        return False
    except Exception as e:
        log(f"  ⚠️ 检查子代理状态失败: {e}")
        return False


def cleanup_zombies(dry_run=False):
    """清理僵尸任务"""
    log(f"\n{'='*60}")
    log(f"=== Watchdog 周期: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===")

    client = KanbanClient()

    # 获取僵尸任务
    zombies = client.get_zombie_tasks(threshold_minutes=ZOMBIE_THRESHOLD_MINUTES)

    if not zombies:
        log("✅ 无僵尸任务")
        return 0

    log(f"发现 {len(zombies)} 个候选僵尸任务")

    cleaned = 0
    for z in zombies:
        task_id = z['id']
        session_key = z.get('subagent_session_key', '')

        # 检查子代理是否存活
        alive = check_subagent_alive(session_key)

        if not alive:
            if dry_run:
                log(f"  [DRY RUN] 清理 #{task_id}: {z['title']} (session: {session_key})")
            else:
                log(f"  🧹 清理 #{task_id}: {z['title']} (session: {session_key})")
                success = client.mark_failed(
                    task_id=task_id,
                    error_reason=f"Watchdog 清理：子代理超时（无心跳 > {ZOMBIE_THRESHOLD_MINUTES} 分钟）"
                )
                if success:
                    cleaned += 1
                    log_to_memory(f"⚠️ Watchdog 清理僵尸任务: #{task_id} - {z['title']}")
                else:
                    log(f"  ❌ 清理失败 #{task_id}")
        else:
            log(f"  ⏭️ 跳过 #{task_id}: 子代理仍存活 (session: {session_key})")

    log(f"\n本轮清理 {cleaned} 个僵尸任务")
    return cleaned


def log_to_memory(msg):
    """追加到 MEMORY.md"""
    try:
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with open(MEMORY_FILE, 'a') as f:
            f.write(f"\n- [{ts}] {msg}")
    except Exception as e:
        log(f"  ⚠️ 写入 MEMORY.md 失败: {e}")


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Scheduler Watchdog')
    parser.add_argument('--dry-run', action='store_true', help='只检测不清理')
    args = parser.parse_args()

    cleanup_zombies(dry_run=args.dry_run)
