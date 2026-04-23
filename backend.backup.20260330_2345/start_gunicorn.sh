#!/bin/bash
# 看板系统后端启动脚本（带环境变量加载）

cd /opt/kanban-react/backend

# 启动 Gunicorn（使用 --env 传递环境变量）
exec /usr/bin/python3 -m gunicorn     --bind 0.0.0.0:8086     --workers 2     --timeout 120     --env DB_TYPE=mysql     --env MYSQL_HOST=rm-2zew4su9p966e8x2ofo.mysql.rds.aliyuncs.com     --env MYSQL_PORT=3306     --env MYSQL_USER=kanban     --env MYSQL_PASSWORD=Irc210Irc210!     --env MYSQL_DATABASE=kanban     --access-logfile access.log     --error-logfile error.log     app:app
