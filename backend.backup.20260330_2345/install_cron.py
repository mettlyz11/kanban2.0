#!/usr/bin/env python3
"""
直接写入 crontab 文件（绕过 crontab 命令）
"""
import os
import subprocess

CRONTAB_FILE = "/tmp/kanban_crontab.txt"
CRON_CONTENT = """# 看板系统前端路由监控
*/5 * * * * cd ~/.openclaw/workspace && python3 scripts/frontend_route_monitor.py >> logs/frontend_monitor/cron.log 2>&1
0 13 * * * /Users/mettlyz/.openclaw/workspace/scripts/run_deep_thinking.sh

# 系统监控数据收集（每 5 分钟）
*/5 * * * * cd /Users/mettlyz/.openclaw/workspace/kanban-react/backend && ./collect_metrics.sh >> /tmp/metrics_collect.log 2>&1
"""

# 写入文件
with open(CRONTAB_FILE, 'w') as f:
    f.write(CRON_CONTENT)

print(f"✅ Crontab 文件已写入：{CRONTAB_FILE}")
print("\n内容预览:")
print(CRON_CONTENT)
print("\n⚠️  请手动执行：crontab /tmp/kanban_crontab.txt")
