#!/bin/bash
# 看板2.4系统备份脚本
# 使用方法: ./backup_kanban.sh [版本号，如 v2.4.5]

# 配置
BACKUP_DIR="/opt/kanban-react/backend"
DB_FILE="$BACKUP_DIR/kanban_v5.db"
FRONTEND_DIR="/opt/kanban-react/frontend/dist"
MAX_BACKUPS=20

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 获取版本号
if [ -z "$1" ]; then
    echo -e "${RED}错误: 请提供版本号${NC}"
    echo "用法: $0 v2.4.x"
    exit 1
fi

VERSION=$1
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
DB_BACKUP="kanban_v5.db.backup_${VERSION}_${TIMESTAMP}"
FRONTEND_BACKUP="frontend_backup_${VERSION}_${TIMESTAMP}.tar.gz"

echo "========================================"
echo "看板2.4系统备份"
echo "版本: $VERSION"
echo "时间: $(date '+%Y-%m-%d %H:%M:%S')"
echo "========================================"

# 1. 检查数据库文件
if [ ! -f "$DB_FILE" ]; then
    echo -e "${RED}错误: 数据库文件不存在: $DB_FILE${NC}"
    exit 1
fi

DB_SIZE=$(stat -c%s "$DB_FILE")
if [ $DB_SIZE -lt 1000000 ]; then
    echo -e "${RED}错误: 数据库文件太小 (${DB_SIZE} bytes)，可能已损坏${NC}"
    exit 1
fi

echo -e "${GREEN}✓ 数据库文件检查通过 (大小: $DB_SIZE bytes)${NC}"

# 2. 备份数据库
echo ""
echo "[1/4] 备份数据库..."
cp "$DB_FILE" "$BACKUP_DIR/$DB_BACKUP"
if [ $? -eq 0 ]; then
    BACKUP_SIZE=$(stat -c%s "$BACKUP_DIR/$DB_BACKUP")
    echo -e "${GREEN}✓ 数据库备份成功: $DB_BACKUP (${BACKUP_SIZE} bytes)${NC}"
else
    echo -e "${RED}✗ 数据库备份失败${NC}"
    exit 1
fi

# 3. 备份前端
echo ""
echo "[2/4] 备份前端文件..."
if [ -d "$FRONTEND_DIR" ]; then
    tar -czf "$BACKUP_DIR/$FRONTEND_BACKUP" -C "$FRONTEND_DIR" .
    if [ $? -eq 0 ]; then
        FRONTEND_SIZE=$(stat -c%s "$BACKUP_DIR/$FRONTEND_BACKUP")
        echo -e "${GREEN}✓ 前端备份成功: $FRONTEND_BACKUP (${FRONTEND_SIZE} bytes)${NC}"
    else
        echo -e "${YELLOW}⚠ 前端备份失败，继续执行...${NC}"
    fi
else
    echo -e "${YELLOW}⚠ 前端目录不存在，跳过前端备份${NC}"
fi

# 4. 清理旧版本
echo ""
echo "[3/4] 清理旧版本（保留最近 $MAX_BACKUPS 个）..."

# 清理旧的数据库备份
echo "  清理数据库备份..."
ls -t $BACKUP_DIR/*.backup_v2.4.* 2>/dev/null | tail -n +$((MAX_BACKUPS + 1)) | while read file; do
    echo "    删除: $(basename $file)"
    rm -f "$file"
done

# 清理旧的前端备份
echo "  清理前端备份..."
ls -t $BACKUP_DIR/frontend_backup_*.tar.gz 2>/dev/null | tail -n +$((MAX_BACKUPS + 1)) | while read file; do
    echo "    删除: $(basename $file)"
    rm -f "$file"
done

# 5. 验证备份
echo ""
echo "[4/4] 验证备份..."
sqlite3 "$BACKUP_DIR/$DB_BACKUP" "SELECT COUNT(*) FROM projects;" > /dev/null 2>&1
if [ $? -eq 0 ]; then
    PROJECT_COUNT=$(sqlite3 "$BACKUP_DIR/$DB_BACKUP" "SELECT COUNT(*) FROM projects;")
    TASK_COUNT=$(sqlite3 "$BACKUP_DIR/$DB_BACKUP" "SELECT COUNT(*) FROM tasks;")
    echo -e "${GREEN}✓ 备份验证通过${NC}"
    echo "  - 项目数: $PROJECT_COUNT"
    echo "  - 任务数: $TASK_COUNT"
else
    echo -e "${RED}✗ 备份验证失败，备份文件可能损坏${NC}"
    exit 1
fi

# 6. 输出回滚命令
echo ""
echo "========================================"
echo -e "${GREEN}备份完成！${NC}"
echo "========================================"
echo "版本: $VERSION"
echo "数据库备份: $DB_BACKUP"
echo "前端备份: $FRONTEND_BACKUP"
echo ""
echo "如果需要回滚，执行以下命令:"
echo "----------------------------------------"
echo "# 停止服务"
echo "pkill -f 'python.*app.py'"
echo ""
echo "# 恢复数据库"
echo "cp $BACKUP_DIR/$DB_BACKUP $DB_FILE"
echo ""
echo "# 恢复前端（可选）"
echo "tar -xzf $BACKUP_DIR/$FRONTEND_BACKUP -C $FRONTEND_DIR"
echo ""
echo "# 重启服务"
echo "cd $BACKUP_DIR && nohup python3 app.py > /var/log/kanban.log 2>&1 &"
echo "----------------------------------------"
echo ""

# 列出当前所有备份
echo "当前备份列表（最近5个）:"
echo "----------------------------------------"
ls -lht $BACKUP_DIR/*.backup_v2.4.* 2>/dev/null | head -5 | awk '{print $9, "(" $5 ")"}'
echo ""
echo "总共备份数:"
echo "  数据库备份: $(ls $BACKUP_DIR/*.backup_v2.4.* 2>/dev/null | wc -l) 个"
echo "  前端备份: $(ls $BACKUP_DIR/frontend_backup_*.tar.gz 2>/dev/null | wc -l) 个"
echo "========================================"
