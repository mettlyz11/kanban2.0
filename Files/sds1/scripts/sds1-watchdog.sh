#!/bin/bash
# SDS1 看门狗

SDS_PID_FILE="/tmp/sds.pid"
SDS_START_SCRIPT="/Users/mettlyz/.openclaw/workspace/sds1/scripts/start_sds.sh"
LOG_FILE="/Users/mettlyz/.openclaw/workspace/sds1/logs/sds1-watchdog.log"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" >> "$LOG_FILE"
}

# 检查 PID 文件
if [ ! -f "$SDS_PID_FILE" ]; then
    log "PID 文件不存在，启动 SDS1..."
    bash "$SDS_START_SCRIPT" > /dev/null 2>&1
    exit 0
fi

SDS_PID=$(cat "$SDS_PID_FILE")

# 检查进程是否存在
if ! ps -p "$SDS_PID" > /dev/null 2>&1; then
    log "SDS1 进程 $SDS_PID 不存在，重启..."
    rm -f "$SDS_PID_FILE"
    bash "$SDS_START_SCRIPT" > /dev/null 2>&1
else
    log "SDS1 进程 $SDS_PID 正常运行"
fi
