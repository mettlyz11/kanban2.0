#!/bin/bash
cd /opt/kanban-react/backend
pkill -9 -f gunicorn
pkill -9 -f 'python.*app.py'
sleep 2

# 使用 socketio.run 启动（支持 WebSocket）
export DB_TYPE=mysql
export MYSQL_HOST=rm-2zew4su9p966e8x2ofo.mysql.rds.aliyuncs.com
export MYSQL_PORT=3306
export MYSQL_USER=kanban
export MYSQL_PASSWORD=Irc210Irc210!
export MYSQL_DATABASE=kanban

nohup python3 app.py > /var/log/kanban_backend.log 2>&1 &

sleep 3
ps aux | grep 'python.*app.py' | grep -v grep
echo "✅ 后端服务已启动 (WebSocket 模式)"
