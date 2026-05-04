#!/bin/bash
# SDS 自我驱动系统 - 重启脚本
# 版本: v4.6
# 作者: Dudu

SCRIPT_DIR="/Users/mettlyz/.openclaw/workspace/sds1/scripts"

echo "🔄 重启 SDS 自我驱动系统..."
$SCRIPT_DIR/stop_sds.sh
sleep 1
$SCRIPT_DIR/start_sds.sh
