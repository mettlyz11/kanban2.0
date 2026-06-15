#!/bin/bash
# 健康周报自动生成脚本 - 配合系统 cron 使用
# 用法: crontab -e 加入以下行:
# 0 20 * * 0 /Users/mettlyz/.openclaw/workspace/output/task-2078/auto_weekly_health.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/健康打卡脚本_daily_health_check_2026-04-26.py"
REPORT_DIR="$HOME/.openclaw/workspace/health_data/reports"

echo "📊 自动生成周健康报告..."
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"

# 创建报告目录
mkdir -p "$REPORT_DIR"

# 生成周报
python3 "$PYTHON_SCRIPT" --weekly > "$REPORT_DIR/weekly_$(date '+%Y-%m-%d').txt" 2>&1

echo "✅ 周报已保存到: $REPORT_DIR/weekly_$(date '+%Y-%m-%d').txt"

# 可选: 显示历史趋势
echo "" >> "$REPORT_DIR/weekly_$(date '+%Y-%m-%d').txt"
echo "📋 最近7天趋势:" >> "$REPORT_DIR/weekly_$(date '+%Y-%m-%d').txt"
python3 "$PYTHON_SCRIPT" --history 7 >> "$REPORT_DIR/weekly_$(date '+%Y-%m-%d').txt" 2>&1

echo "✅ 完成！"
