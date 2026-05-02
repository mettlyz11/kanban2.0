#!/bin/bash
# SDS 自我驱动系统 - 停止脚本
# 版本: v4.6
# 作者: Dudu

PID_FILE="/tmp/sds1.pid"

if [ -f "$PID_FILE" ]; then
    PID=$(cat $PID_FILE)
    if ps -p $PID > /dev/null 2>&1; then
        echo "🛑 正在停止 SDS (PID: $PID)..."
        kill $PID
        sleep 2
        if ps -p $PID > /dev/null 2>&1; then
            echo "⚠️  进程未响应，强制终止..."
            kill -9 $PID
        fi
        echo "✅ SDS 已停止"
    else
        echo "⚠️  PID 文件存在但进程未运行"
    fi
    rm $PID_FILE
else
    echo "ℹ️  SDS 未在运行"
fi
