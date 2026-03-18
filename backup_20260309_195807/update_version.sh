#!/bin/bash
# update_version.sh - 更新版本记录

VERSION=$1
REASON=$2
DATE=$(date +%Y%m%d_%H%M%S)

if [ -z "$VERSION" ]; then
    echo "用法: $0 v2.4.x '更新原因'"
    exit 1
fi

VERSION_FILE="/opt/kanban-react/backend/VERSION"

echo "更新版本记录: $VERSION ($DATE)"

# 读取当前版本
CURRENT=$(grep "CURRENT_VERSION=" $VERSION_FILE | cut -d= -f2)

# 更新VERSION文件
sed -i "s/CURRENT_VERSION=.*/CURRENT_VERSION=$VERSION/" $VERSION_FILE
sed -i "s/LAST_UPDATE=.*/LAST_UPDATE=$DATE/" $VERSION_FILE
sed -i "s/UPDATE_REASON=.*/UPDATE_REASON=$REASON/" $VERSION_FILE

# 添加版本历史
sed -i "/## 版本历史/a\- $VERSION ($DATE) - 当前版本 - $REASON" $VERSION_FILE

echo "✅ 版本记录已更新: $VERSION"
cat $VERSION_FILE | head -15
