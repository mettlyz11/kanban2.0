#!/bin/bash
# 启动看板后端 - 使用 RDS MySQL

# 设置 RDS 密码（从环境变量或命令行参数获取）
if [ -z "$MYSQL_PASSWORD" ]; then
    if [ -z "$1" ]; then
        echo "错误: 请提供 RDS 密码"
        echo "用法: $0 <RDS密码>"
        echo "或设置环境变量: export MYSQL_PASSWORD=<密码>"
        exit 1
    fi
    export MYSQL_PASSWORD="$1"
fi

# 设置数据库类型为 MySQL
export DB_TYPE=mysql
export MYSQL_HOST=rm-2zew4su9p966e8x2ofo.mysql.rds.aliyuncs.com
export MYSQL_PORT=3306
export MYSQL_USER=kanban
export MYSQL_DATABASE=kanban

echo "🗄️ 启动看板后端 (RDS 模式)"
echo "================================"
echo "数据库类型: MySQL (RDS)"
echo "RDS 地址: $MYSQL_HOST"
echo "数据库: $MYSQL_DATABASE"
echo "================================"

# 检查依赖
if ! python3 -c "import pymysql" 2>/dev/null; then
    echo "安装 PyMySQL..."
    pip3 install pymysql -q
fi

# 启动后端
cd "$(dirname "$0")"
python3 app.py
