#!/bin/bash
# 看板系统后端启动脚本（带环境变量加载）

cd /opt/kanban-react/backend

# 显式设置环境变量
export DB_TYPE=mysql
export MYSQL_HOST=rm-2zew4su9p966e8x2ofo.mysql.rds.aliyuncs.com
export MYSQL_PORT=3306
export MYSQL_USER=kanban
export MYSQL_PASSWORD=Irc210Irc210!
export MYSQL_DATABASE=kanban

# 打印配置（调试用）
echo "启动后端服务..."
echo "DB_TYPE: $DB_TYPE"
echo "MYSQL_HOST: $MYSQL_HOST"

# 启动 Gunicorn
exec /usr/bin/python3 -m gunicorn \
    --bind 0.0.0.0:8086 \
    --workers 2 \
    --timeout 120 \
    --access-logfile access.log \
    --error-logfile error.log \
    app:app
