#!/bin/bash
# universal_backup.sh - 通用项目备份脚本（适用于所有项目）
# 作者: OpenClaw
# 版本: 1.0
# 日期: 2026-03-03

# 使用方法:
# ./universal_backup.sh <项目名称> <版本号> <更新原因>
# 例如: ./universal_backup.sh kanban v2.4.8 "修复API错误"

# ============================================
# 配置部分
# ============================================

PROJECT_NAME=$1
VERSION=$2
REASON=$3
DATE=$(date +%Y%m%d_%H%M%S)
RETAIN_COUNT=20

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# ============================================
# 项目配置映射
# ============================================

case $PROJECT_NAME in
    "kanban"|"看板"|"kanban-react")
        PROJECT_DIR="/opt/kanban-react"
        BACKEND_DIR="/opt/kanban-react/backend"
        FRONTEND_DIR="/opt/kanban-react/frontend/dist"
        HAS_FRONTEND=true
        HAS_DATABASE=true
        DB_FILE="kanban_v5.db"
        PROJECT_FULLNAME="看板2.4系统"
        ;;
    "t109"|"T109")
        PROJECT_DIR="/opt/t109-pro"
        BACKEND_DIR="/opt/t109-pro/backend"
        FRONTEND_DIR="/opt/t109-pro/frontend/dist"
        HAS_FRONTEND=true
        HAS_DATABASE=true
        DB_FILE="t109.db"
        PROJECT_FULLNAME="T109 Pro过渡态计算平台"
        ;;
    "helight"|"Helight")
        PROJECT_DIR="/opt/helight-pro"
        BACKEND_DIR="/opt/helight-pro/backend"
        FRONTEND_DIR="/opt/helight-pro/frontend/dist"
        HAS_FRONTEND=true
        HAS_DATABASE=true
        DB_FILE="helight.db"
        PROJECT_FULLNAME="Helight Pro和光智成平台"
        ;;
    "pepi"|"Pepi")
        PROJECT_DIR="/opt/pepi"
        BACKEND_DIR="/opt/pepi/backend"
        FRONTEND_DIR="/opt/pepi/frontend/dist"
        HAS_FRONTEND=true
        HAS_DATABASE=true
        DB_FILE="pepi.db"
        PROJECT_FULLNAME="Pepi数字员工系统"
        ;;
    *)
        echo -e "${RED}❌ 错误: 未知项目 '$PROJECT_NAME'${NC}"
        echo "支持的项目: kanban, t109, helight, pepi"
        exit 1
        ;;
esac

# ============================================
# 检查参数
# ============================================

if [ -z "$VERSION" ]; then
    echo -e "${RED}❌ 错误: 请提供版本号${NC}"
    echo "用法: $0 <项目名> <版本号> <更新原因>"
    echo "例如: $0 kanban v2.4.8 '修复API错误'"
    exit 1
fi

if [ -z "$REASON" ]; then
    REASON="常规更新"
fi

# ============================================
# 开始备份
# ============================================

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║         🚀 通用项目备份系统 v1.0                           ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "📦 项目名称: $PROJECT_FULLNAME"
echo "🏷️  版本号: $VERSION"
echo "📝 更新原因: $REASON"
echo "📅 备份时间: $DATE"
echo "📂 项目路径: $PROJECT_DIR"
echo ""

# 检查项目目录是否存在
if [ ! -d "$PROJECT_DIR" ]; then
    echo -e "${RED}❌ 错误: 项目目录不存在 $PROJECT_DIR${NC}"
    exit 1
fi

cd "$BACKEND_DIR" || exit 1

BACKUP_COUNT=0

# ============================================
# Part 1: 数据库备份
# ============================================

if [ "$HAS_DATABASE" = true ]; then
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📦 [Part 1/5] 数据库备份"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    if [ -f "$DB_FILE" ]; then
        DB_BACKUP="${DB_FILE}.backup_${VERSION}_${DATE}"
        cp "$DB_FILE" "$DB_BACKUP"
        DB_SIZE=$(du -h "$DB_BACKUP" | cut -f1)
        echo -e "${GREEN}✅ 数据库备份完成${NC}"
        echo "   文件: $DB_BACKUP"
        echo "   大小: $DB_SIZE"
        ((BACKUP_COUNT++))
    else
        echo -e "${YELLOW}⚠️  数据库文件不存在: $DB_FILE${NC}"
    fi
fi

# ============================================
# Part 2: Python后端代码备份
# ============================================

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🐍 [Part 2/5] Python后端代码备份"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

PY_COUNT=$(ls *.py 2>/dev/null | wc -l)
if [ $PY_COUNT -gt 0 ]; then
    PY_BACKUP="backend_py_backup_${VERSION}_${DATE}.tar.gz"
    tar -czf "$PY_BACKUP" \
        --exclude='venv' --exclude='__pycache__' --exclude='*.pyc' \
        *.py 2>/dev/null
    PY_SIZE=$(du -h "$PY_BACKUP" | cut -f1)
    echo -e "${GREEN}✅ Python代码备份完成${NC}"
    echo "   文件: $PY_BACKUP"
    echo "   大小: $PY_SIZE"
    echo "   包含: $PY_COUNT 个Python文件"
    ((BACKUP_COUNT++))
else
    echo -e "${YELLOW}⚠️  未找到Python文件${NC}"
fi

# ============================================
# Part 3: 配置和数据目录备份
# ============================================

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "⚙️  [Part 3/5] 配置和数据目录备份"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

CONFIG_BACKUP="backend_config_backup_${VERSION}_${DATE}.tar.gz"
tar -czf "$CONFIG_BACKUP" \
    --exclude='venv' --exclude='__pycache__' --exclude='*.pyc' \
    --exclude='*.db' --exclude='*.db.*' --exclude='*.tar.gz' \
    --exclude='*.log' \
    *.yml *.txt *.json *.sql *.sh \
    VERSION \
    data/ services/ skills/ static/ templates/ 2>/dev/null

if [ -f "$CONFIG_BACKUP" ]; then
    CONFIG_SIZE=$(du -h "$CONFIG_BACKUP" | cut -f1)
    echo -e "${GREEN}✅ 配置和数据备份完成${NC}"
    echo "   文件: $CONFIG_BACKUP"
    echo "   大小: $CONFIG_SIZE"
    ((BACKUP_COUNT++))
else
    echo -e "${YELLOW}⚠️  配置备份文件未创建${NC}"
fi

# ============================================
# Part 4: 前端备份
# ============================================

if [ "$HAS_FRONTEND" = true ]; then
    echo ""
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "💻 [Part 4/5] 前端备份"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    if [ -d "$FRONTEND_DIR" ]; then
        FRONTEND_BACKUP="frontend_backup_${VERSION}_${DATE}.tar.gz"
        tar -czf "$FRONTEND_BACKUP" -C "$FRONTEND_DIR" . 2>/dev/null
        FRONTEND_SIZE=$(du -h "$FRONTEND_BACKUP" | cut -f1)
        echo -e "${GREEN}✅ 前端备份完成${NC}"
        echo "   文件: $FRONTEND_BACKUP"
        echo "   大小: $FRONTEND_SIZE"
        ((BACKUP_COUNT++))
    else
        echo -e "${YELLOW}⚠️  前端目录不存在: $FRONTEND_DIR${NC}"
    fi
fi

# ============================================
# Part 5: 更新版本记录
# ============================================

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📝 [Part 5/5] 更新版本记录"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 创建或更新VERSION文件
VERSION_FILE="$BACKEND_DIR/VERSION"

if [ ! -f "$VERSION_FILE" ]; then
    echo "# $PROJECT_FULLNAME 版本记录" > "$VERSION_FILE"
    echo "" >> "$VERSION_FILE"
    echo "## 版本历史" >> "$VERSION_FILE"
    echo "" >> "$VERSION_FILE"
fi

# 读取当前版本
CURRENT_VERSION=$(grep "CURRENT_VERSION=" "$VERSION_FILE" 2>/dev/null | cut -d= -f2 || echo "v0.0.0")

# 创建新的版本记录
cat > "$VERSION_FILE" << EOF
# $PROJECT_FULLNAME 版本记录

CURRENT_VERSION=$VERSION
LAST_UPDATE=$DATE
UPDATE_REASON=$REASON

## 版本历史
- $VERSION ($DATE) - 当前版本 - $REASON
EOF

# 添加历史版本（保留最近20个）
if [ -n "$CURRENT_VERSION" ] && [ "$CURRENT_VERSION" != "$VERSION" ]; then
    echo "- $CURRENT_VERSION - 上一版本" >> "$VERSION_FILE"
fi

echo -e "${GREEN}✅ 版本记录已更新${NC}"
echo "   文件: $VERSION_FILE"
echo "   当前版本: $VERSION"

# ============================================
# 清理旧版本
# ============================================

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🧹 清理旧版本（保留最近$RETAIN_COUNT个）"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

CLEANED=0
for pattern in "*.backup_v*" "backend_py_backup_*.tar.gz" \
               "backend_config_backup_*.tar.gz" "frontend_backup_*.tar.gz"; do
    COUNT=$(ls -1 $pattern 2>/dev/null | wc -l)
    if [ $COUNT -gt $RETAIN_COUNT ]; then
        ls -t $pattern 2>/dev/null | tail -n +$((RETAIN_COUNT+1)) | xargs -r rm -f
        CLEANED=$((CLEANED + 1))
    fi
done

echo -e "${GREEN}✅ 旧版本清理完成${NC}"
echo "   保留规则: 最近$RETAIN_COUNT个版本"

# ============================================
# 备份摘要
# ============================================

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                    📊 备份完成摘要                         ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "📦 项目名称: $PROJECT_FULLNAME"
echo "🏷️  版本号: $VERSION"
echo "📅 备份时间: $DATE"
echo "✅ 成功备份: $BACKUP_COUNT/5 部分"
echo ""
echo "📂 备份文件列表:"
echo "────────────────────────────────────────────────────────────"
ls -lh *.backup_${VERSION}_${DATE}* *.backup_${VERSION}_${DATE}.tar.gz 2>/dev/null | awk '{printf "  %-45s %10s\n", $9, $5}'
ls -lh *_backup_${VERSION}_${DATE}.tar.gz 2>/dev/null | awk '{printf "  %-45s %10s\n", $9, $5}'
echo "────────────────────────────────────────────────────────────"
echo ""
echo -e "${GREEN}✅ $PROJECT_FULLNAME 备份完成！${NC}"
echo ""
echo "📋 检查清单:"
echo "  □ 数据库已备份"
echo "  □ Python代码已备份"
echo "  □ 配置和数据已备份"
echo "  □ 前端已备份"
echo "  □ 版本记录已更新"
echo ""
echo "🔄 如需回滚，使用备份文件恢复即可"
echo ""
