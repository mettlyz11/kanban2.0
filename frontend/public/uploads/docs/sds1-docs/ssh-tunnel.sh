#!/bin/bash
# SSH 隧道自动重连脚本

HOST="root@47.93.184.128"
LOCAL_PORT=13306
REMOTE_HOST="rm-2zew4su9p966e8x2ofo.mysql.rds.aliyuncs.com"
REMOTE_PORT=3306
LOG_FILE="$HOME/.openclaw/workspace/sds1/logs/ssh-tunnel.log"
CHECK_INTERVAL=180  # 每3分钟检查一次

mkdir -p "$(dirname "$LOG_FILE")"

echo "[$(date)] SSH隧道监控启动 (检查间隔: ${CHECK_INTERVAL}秒)" >> "$LOG_FILE"

while true; do
    # 检查隧道是否存活
    if ! nc -z 127.0.0.1 $LOCAL_PORT 2>/dev/null; then
        echo "[$(date)] 隧道断开，尝试重连..." >> "$LOG_FILE"
        
        # 杀死旧进程
        pkill -f "ssh.*$LOCAL_PORT:$REMOTE_HOST:$REMOTE_PORT" 2>/dev/null
        sleep 1
        
        # 建立新隧道
        ssh -N -o ServerAliveInterval=30 -o ServerAliveCountMax=3 \
            -L $LOCAL_PORT:$REMOTE_HOST:$REMOTE_PORT \
            $HOST > /dev/null 2>&1 &
        
        sleep 3
        
        if nc -z 127.0.0.1 $LOCAL_PORT 2>/dev/null; then
            echo "[$(date)] 隧道重连成功 (PID: $!)" >> "$LOG_FILE"
        else
            echo "[$(date)] 隧道重连失败，60秒后重试" >> "$LOG_FILE"
            sleep 60
            continue
        fi
    fi
    
    # 每3分钟检查一次
    sleep $CHECK_INTERVAL
done
