#!/bin/bash
# 看板系统后端启动脚本 - 支持 WebSocket

cd /opt/kanban-react/backend

# 停止现有进程
pkill -f 'gunicorn.*kanban' || true
sleep 2

# 使用 socketio 启动
export DB_TYPE=mysql
export MYSQL_HOST=rm-2zew4su9p966e8x2ofo.mysql.rds.aliyuncs.com
export MYSQL_PORT=3306
export MYSQL_USER=kanban
export MYSQL_PASSWORD=Irc210Irc210!
export MYSQL_DATABASE=kanban

nohup python3 app.py > /var/log/kanban_backend.log 2>&1 &

echo "✅ 后端服务已启动 (WebSocket 模式)"
sleep 3
tail -50 /var/log/kanban_backend.log
