#!/bin/bash
# SDS1 看门狗

SDS_PID_FILE="/tmp/sds.pid"
SDS_START_CMD="cd /Users/mettlyz/.openclaw/workspace/sds1 && nohup python3 sds_main.py --continuous > /dev/null 2>&1 &"
LOG_FILE="/Users/mettlyz/.openclaw/workspace/sds1/logs/sds1-watchdog.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

# 检查 PID 文件
if [ ! -f "$SDS_PID_FILE" ]; then
    log "PID 文件不存在，启动 SDS1..."
    eval "$SDS_START_CMD"
    echo $! > "$SDS_PID_FILE"
    log "SDS1 已启动，PID: $!"
    exit 0
fi

SDS_PID=$(cat "$SDS_PID_FILE" 2>/dev/null)

# 检查进程是否存在
if ! ps -p "$SDS_PID" > /dev/null 2>&1; then
    log "SDS1 进程 $SDS_PID 不存在，重新启动..."
    eval "$SDS_START_CMD"
    echo $! > "$SDS_PID_FILE"
    log "SDS1 已重启，PID: $!"
else
    # 检查进程是否卡死（超过30分钟无输出）
    LAST_LOG=$(stat -f "%m" /Users/mettlyz/.openclaw/workspace/sds1/logs/sds-main.log 2>/dev/null)
    CURRENT_TIME=$(date +%s)
    TIME_DIFF=$((CURRENT_TIME - LAST_LOG))
    
    if [ "$TIME_DIFF" -gt 3600 ]; then
        log "SDS1 可能卡死（${TIME_DIFF}秒无日志），重启..."
        kill "$SDS_PID" 2>/dev/null
        sleep 2
        eval "$SDS_START_CMD"
        echo $! > "$SDS_PID_FILE"
        log "SDS1 已强制重启，PID: $!"
    fi
fi
