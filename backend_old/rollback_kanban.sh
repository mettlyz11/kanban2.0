#!/bin/bash
# 看板2.4系统回滚脚本
# 使用方法: ./rollback_kanban.sh [版本号，如 v2.4.5]

# 配置
BACKUP_DIR="/opt/kanban-react/backend"
DB_FILE="$BACKUP_DIR/kanban_v5.db"
FRONTEND_DIR="/opt/kanban-react/frontend/dist"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "========================================"
echo "看板2.4系统回滚"
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================"

# 1. 列出所有可用版本
echo ""
echo "[1/3] 可用版本列表:"
echo "----------------------------------------"

BACKUP_LIST=$(ls -t $BACKUP_DIR/*.backup_v2.4.* 2>/dev/null)
if [ -z "$BACKUP_LIST" ]; then
    echo -e "${RED}错误: 没有找到备份文件${NC}"
    exit 1
fi

# 显示备份列表
echo -e "${BLUE}最近10个可用版本:${NC}"
echo ""
COUNTER=1
ls -t $BACKUP_DIR/*.backup_v2.4.* 2>/dev/null | head -10 | while read file; do
    FILENAME=$(basename $file)
    SIZE=$(stat -c%s "$file")
    SIZE_MB=$(echo "scale=2; $SIZE / 1024 / 1024" | bc)
    
    # 提取版本号和时间
    VERSION=$(echo $FILENAME | grep -oP 'backup_v\d+\.\d+\.\d+' | sed 's/backup_//')
    TIMESTAMP=$(echo $FILENAME | grep -oP '\d{8}_\d{6}')
    
    # 获取数据库统计
    PROJECT_COUNT=$(sqlite3 "$file" "SELECT COUNT(*) FROM projects;" 2>/dev/null || echo "N/A")
    TASK_COUNT=$(sqlite3 "$file" "SELECT COUNT(*) FROM tasks;" 2>/dev/null || echo "N/A")
    
    echo -e "${GREEN}$COUNTER)${NC} $VERSION"
    echo "   文件: $FILENAME"
    echo "   时间: $(date -d "${TIMESTAMP:0:8} ${TIMESTAMP:9:2}:${TIMESTAMP:11:2}:${TIMESTAMP:13:2}" '+%Y-%m-%d %H:%M:%S' 2>/dev/null || echo $TIMESTAMP)"
    echo "   大小: ${SIZE_MB}MB"
    echo "   数据: $PROJECT_COUNT 项目, $TASK_COUNT 任务"
    echo ""
    
    COUNTER=$((COUNTER + 1))
done

echo "----------------------------------------"

# 2. 选择版本
if [ -z "$1" ]; then
    echo -n "请输入要回滚的版本号 (如 v2.4.5) 或序号 (如 1): "
    read VERSION
else
    VERSION=$1
fi

# 判断是序号还是版本号
if [[ "$VERSION" =~ ^[0-9]+$ ]]; then
    # 是序号
    SELECTED_FILE=$(ls -t $BACKUP_DIR/*.backup_v2.4.* 2>/dev/null | sed -n "${VERSION}p")
    if [ -z "$SELECTED_FILE" ]; then
        echo -e "${RED}错误: 序号 $VERSION 无效${NC}"
        exit 1
    fi
else
    # 是版本号
    SELECTED_FILE=$(ls -t $BACKUP_DIR/*.backup_$VERSION* 2>/dev/null | head -1)
    if [ -z "$SELECTED_FILE" ]; then
        echo -e "${RED}错误: 版本 $VERSION 不存在${NC}"
        exit 1
    fi
fi

SELECTED_NAME=$(basename $SELECTED_FILE)
echo ""
echo -e "${YELLOW}已选择: $SELECTED_NAME${NC}"

# 3. 确认回滚
echo ""
echo -e "${RED}警告: 回滚将覆盖当前数据库！${NC}"
echo -n "确定要回滚吗？当前数据将丢失！(yes/no): "
read CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "已取消回滚"
    exit 0
fi

# 4. 执行回滚
echo ""
echo "[2/3] 执行回滚..."

# 4.1 停止服务
echo "  停止服务..."
pkill -f 'python.*app.py' 2>/dev/null
systemctl stop nginx 2>/dev/null || service nginx stop 2>/dev/null
sleep 2
echo -e "  ${GREEN}✓ 服务已停止${NC}"

# 4.2 备份当前数据（以防万一）
echo "  备份当前数据..."
CURRENT_BACKUP="kanban_v5.db.before_rollback_$(date +%Y%m%d_%H%M%S)"
cp "$DB_FILE" "$BACKUP_DIR/$CURRENT_BACKUP"
echo -e "  ${GREEN}✓ 当前数据已备份: $CURRENT_BACKUP${NC}"

# 4.3 恢复数据库
echo "  恢复数据库..."
cp "$SELECTED_FILE" "$DB_FILE"
if [ $? -eq 0 ]; then
    echo -e "  ${GREEN}✓ 数据库已恢复${NC}"
else
    echo -e "  ${RED}✗ 数据库恢复失败${NC}"
    exit 1
fi

# 4.4 恢复前端（如果有对应的前端备份）
SELECTED_VERSION=$(echo $SELECTED_NAME | grep -oP 'v\d+\.\d+\.\d+')
FRONTEND_BACKUP=$(ls -t $BACKUP_DIR/frontend_backup_${SELECTED_VERSION}_*.tar.gz 2>/dev/null | head -1)

if [ -f "$FRONTEND_BACKUP" ]; then
    echo "  恢复前端..."
    rm -rf ${FRONTEND_DIR}/*
    tar -xzf "$FRONTEND_BACKUP" -C "$FRONTEND_DIR"
    if [ $? -eq 0 ]; then
        echo -e "  ${GREEN}✓ 前端已恢复${NC}"
    else
        echo -e "  ${YELLOW}⚠ 前端恢复失败，继续执行...${NC}"
    fi
else
    echo -e "  ${YELLOW}⚠ 未找到对应的前端备份，跳过${NC}"
fi

# 4.5 重启服务
echo "  重启服务..."
cd $BACKUP_DIR && nohup python3 app.py > /var/log/kanban.log 2>&1 &
sleep 3
systemctl start nginx 2>/dev/null || service nginx start 2>/dev/null
echo -e "  ${GREEN}✓ 服务已重启${NC}"

# 5. 验证
echo ""
echo "[3/3] 验证回滚结果..."
sleep 3

HEALTH=$(curl -s http://localhost:8086/api/health | grep -o '"status".*"healthy"')
if [ ! -z "$HEALTH" ]; then
    echo -e "  ${GREEN}✓ 服务健康检查通过${NC}"
else
    echo -e "  ${YELLOW}⚠ 服务健康检查异常${NC}"
fi

PROJECT_COUNT=$(curl -s http://localhost:8086/api/projects | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('projects', [])))" 2>/dev/null || echo "N/A")
TASK_COUNT=$(curl -s http://localhost:8086/api/tasks | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('tasks', [])))" 2>/dev/null || echo "N/A")

echo "  当前数据:"
echo "    项目数: $PROJECT_COUNT"
echo "    任务数: $TASK_COUNT"

echo ""
echo "========================================"
echo -e "${GREEN}回滚完成！${NC}"
echo "========================================"
echo "回滚版本: $SELECTED_VERSION"
echo "回滚文件: $SELECTED_NAME"
echo ""
echo "如果回滚后仍有问题，请检查:"
echo "  1. 浏览器缓存（Ctrl+Shift+R强制刷新）"
echo "  2. Nginx配置（systemctl status nginx）"
echo "  3. 后端日志（tail -f /var/log/kanban.log）"
echo "========================================"
