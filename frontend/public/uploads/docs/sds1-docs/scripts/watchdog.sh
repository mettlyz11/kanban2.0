#!/bin/bash
# SDS 看门狗脚本 — 简单模式：只要PID存活就认为正常

SDS_PID_FILE="/tmp/sds.pid"
SDS_START_SCRIPT="/Users/mettlyz/.openclaw/workspace/sds/scripts/start_sds.sh"
LOG_FILE="/Users/mettlyz/.openclaw/workspace/logs/sds-watchdog.log"

# 日志函数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

# 防止竞态 — 检查是否已有 watchdog 在运行
if pgrep -f "watchdog.sh" | grep -v $$ > /dev/null 2>&1; then
    exit 0
fi

# 检查SDS进程是否在运行
check_sds_running() {
    # 方法1: 检查PID文件
    if [ -f "$SDS_PID_FILE" ]; then
        PID=$(cat "$SDS_PID_FILE" 2>/dev/null)
        if [ -n "$PID" ] && ps -p "$PID" > /dev/null 2>&1; then
            return 0
        fi
    fi
    
    # 方法2: 直接查找进程名
    if pgrep -f "sds_main.py --continuous" > /dev/null 2>&1; then
        REAL_PID=$(pgrep -f "sds_main.py --continuous" | head -1)
        echo "$REAL_PID" > "$SDS_PID_FILE"
        return 0
    fi
    
    return 1
}

# 清理所有残留进程
cleanup_residual() {
    log "🧹 清理残留SDS进程..."
    pkill -f "sds_main.py --continuous" 2>/dev/null
    sleep 2
    pkill -9 -f "sds_main.py --continuous" 2>/dev/null
    sleep 1
    rm -f "$SDS_PID_FILE"
}

# 主逻辑
log "🔍 检查SDS进程状态..."

if check_sds_running; then
    PID=$(cat "$SDS_PID_FILE" 2>/dev/null)
    log "✅ SDS进程运行正常 (PID: $PID)"
    exit 0
else
    log "⚠️  SDS进程未运行，执行清理并自动拉起..."
    cleanup_residual
    
    cd /Users/mettlyz/.openclaw/workspace
    bash "$SDS_START_SCRIPT"
    
    sleep 3
    
    if check_sds_running; then
        NEW_PID=$(cat "$SDS_PID_FILE" 2>/dev/null)
        log "🎉 SDS进程自动拉起成功！ (PID: $NEW_PID)"
    else
        log "❌ SDS进程自动拉起失败！"
    fi
fi
