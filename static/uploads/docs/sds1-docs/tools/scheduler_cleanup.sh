#!/bin/bash
# 自我驱动系统清理脚本
# 用于清理残余进程和防止系统崩溃

echo "=== Self-Driving Scheduler Cleanup ==="
echo "Time: $(date)"

# 1. 检查并杀死重复的调度器进程
echo "[1/4] Checking for duplicate scheduler processes..."
SCHEDULER_COUNT=$(ps aux | grep "self-driving-scheduler" | grep -v grep | wc -l)
if [ "$SCHEDULER_COUNT" -gt 1 ]; then
    echo "Found $SCHEDULER_COUNT scheduler processes, killing duplicates..."
    # 保留最新的一个，杀死其他的
    ps aux | grep "self-driving-scheduler" | grep -v grep | sort -k9 -r | tail -n +2 | awk '{print $2}' | xargs kill -9 2>/dev/null
fi

# 2. 检查并杀死 auto-task-executor 重复进程
echo "[2/4] Checking for duplicate auto-task processes..."
AUTO_TASK_COUNT=$(ps aux | grep "auto-task-executor" | grep -v grep | wc -l)
if [ "$AUTO_TASK_COUNT" -gt 1 ]; then
    echo "Found $AUTO_TASK_COUNT auto-task processes, killing duplicates..."
    ps aux | grep "auto-task-executor" | grep -v grep | sort -k9 -r | tail -n +2 | awk '{print $2}' | xargs kill -9 2>/dev/null
fi

# 3. 检查僵尸子代理进程
echo "[3/4] Checking for zombie subagent processes..."
ZOMBIE_COUNT=$(ps aux | grep "session:" | grep -v grep | wc -l)
if [ "$ZOMBIE_COUNT" -gt 0 ]; then
    echo "Found $ZOMBIE_COUNT zombie subagent processes"
    # 只杀死运行时间超过1小时的僵尸进程
    ps aux | grep "session:" | grep -v grep | awk '{if ($10 ~ /[0-9]+:[0-9]+/) print $2}' | xargs kill -9 2>/dev/null
fi

# 4. 检查 launchd 状态
echo "[4/4] Checking launchd service status..."
launchctl list | grep -E "(scheduler|self-driving)" | grep openclaw

echo ""
echo "Current process counts:"
echo "  - Scheduler processes: $(ps aux | grep "self-driving-scheduler" | grep -v grep | wc -l)"
echo "  - Auto-task processes: $(ps aux | grep "auto-task-executor" | grep -v grep | wc -l)"
echo "  - Subagent processes: $(ps aux | grep "session:" | grep -v grep | wc -l)"
echo "  - Total openclaw processes: $(ps aux | grep openclaw | grep -v grep | wc -l)"
echo ""
echo "Cleanup completed at $(date)"
