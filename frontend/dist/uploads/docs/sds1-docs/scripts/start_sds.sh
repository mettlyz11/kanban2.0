#!/bin/bash
# SDS 启动脚本 — 严格单实例控制（跨平台锁）

SDS_DIR="/Users/mettlyz/.openclaw/workspace/sds1"
LOG_DIR="/Users/mettlyz/.openclaw/workspace/sds1/logs"
PID_FILE="/tmp/sds1.pid"

# 日志函数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_DIR/sds-start.log"
}

# 防止竞态 — 检查是否已有启动脚本在运行
if pgrep -f "start_sds.sh" | grep -v $$ > /dev/null 2>&1; then
    log "🔒 另一个启动操作正在进行中，跳过"
    exit 1
fi

# 严格的单实例检查
check_existing() {
    # 方法1: PID文件
    if [ -f "$PID_FILE" ]; then
        OLD_PID=$(cat "$PID_FILE" 2>/dev/null)
        if [ -n "$OLD_PID" ] && ps -p "$OLD_PID" > /dev/null 2>&1; then
            log "⚠️  SDS 已在运行 (PID: $OLD_PID)，拒绝重复启动"
            return 1
        fi
    fi
    
    # 方法2: 进程名检查
    EXISTING=$(pgrep -f "sds_main.py --continuous" | grep -v $$ | head -1)
    if [ -n "$EXISTING" ]; then
        log "⚠️  发现残留进程 (PID: $EXISTING)，先终止..."
        kill "$EXISTING" 2>/dev/null
        sleep 2
        kill -9 "$EXISTING" 2>/dev/null
        sleep 1
    fi
    
    return 0
}

# 主逻辑
log "🚀 启动 SDS v4.6..."

if ! check_existing; then
    exit 1
fi

# 导出 API Key 环境变量
if [ -f /Users/mettlyz/.openclaw/.env ]; then
    set -a
    source /Users/mettlyz/.openclaw/.env
    set +a
    log "✅ 已加载环境变量"
fi

# 启动 SDS
cd "$SDS_DIR"
nohup python3 sds_main.py --continuous >> "$LOG_DIR/sds-main.log" 2>&1 &
NEW_PID=$!

# 写入 PID 文件
echo "$NEW_PID" > "$PID_FILE"

sleep 2

# 验证启动
if ps -p "$NEW_PID" > /dev/null 2>&1; then
    log "✅ SDS v4.6 启动成功 (PID: $NEW_PID)"
    exit 0
else
    log "❌ SDS 启动失败"
    rm -f "$PID_FILE"
    exit 1
fi
