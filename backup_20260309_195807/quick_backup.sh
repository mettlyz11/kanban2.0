#!/bin/bash
# quick_backup.sh - 看板快速备份

if [ $# -lt 2 ]; then
    echo "用法: $0 <版本号> <更新原因>"
    echo "例如: $0 v2.4.8 '修复API错误'"
    exit 1
fi

cd /opt/kanban-react/backend
./universal_backup.sh kanban "$1" "$2"
