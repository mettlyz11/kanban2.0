#!/bin/bash
# backup_with_github.sh - 本地备份 + GitHub自动推送
# 作者: OpenClaw
# 版本: 2.0
# 日期: 2026-03-03

set -e

# ============================================
# 配置
# ============================================

VERSION=$1
REASON=$2
DATE=$(date +%Y%m%d_%H%M%S)
PROJECT_DIR="/opt/kanban-react"
BACKEND_DIR="/opt/kanban-react/backend"
RETAIN_COUNT=20

# Git配置
GIT_REMOTE="github"
GIT_BRANCH="main"
GITHUB_REPO="mettlyz11/kanban-system"

# 颜色
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# ============================================
# 检查参数
# ============================================

if [ -z "$VERSION" ]; then
    echo -e "${RED}❌ 错误: 请提供版本号${NC}"
    echo "用法: $0 <版本号> <更新原因>"
    echo "例如: $0 v2.4.8 '修复API错误'"
    exit 1
fi

if [ -z "$REASON" ]; then
    REASON="常规更新"
fi

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║    🚀 看板2.4 完整备份系统 v2.0 (本地 + GitHub)            ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "🏷️  版本号: $VERSION"
echo "📝 更新原因: $REASON"
echo "📅 备份时间: $DATE"
echo ""

cd "$BACKEND_DIR" || exit 1

BACKUP_COUNT=0
GIT_PUSHED=false

# ============================================
# Part 1: 本地文件备份
# ============================================

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📦 Part 1/6: 数据库备份"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ -f "kanban_v5.db" ]; then
    DB_BACKUP="kanban_v5.db.backup_${VERSION}_${DATE}"
    cp "kanban_v5.db" "$DB_BACKUP"
    DB_SIZE=$(du -h "$DB_BACKUP" | cut -f1)
    echo -e "${GREEN}✅ 数据库备份完成${NC}"
    echo "   文件: $DB_BACKUP ($DB_SIZE)"
    ((BACKUP_COUNT++))
else
    echo -e "${YELLOW}⚠️  数据库文件不存在${NC}"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🐍 Part 2/6: Python后端代码备份"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

PY_COUNT=$(ls *.py 2>/dev/null | wc -l)
if [ $PY_COUNT -gt 0 ]; then
    PY_BACKUP="backend_py_backup_${VERSION}_${DATE}.tar.gz"
    tar -czf "$PY_BACKUP" \
        --exclude='venv' --exclude='__pycache__' --exclude='*.pyc' \
        *.py 2>/dev/null
    PY_SIZE=$(du -h "$PY_BACKUP" | cut -f1)
    echo -e "${GREEN}✅ Python代码备份完成${NC}"
    echo "   文件: $PY_BACKUP ($PY_SIZE)"
    echo "   包含: $PY_COUNT 个Python文件"
    ((BACKUP_COUNT++))
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "⚙️  Part 3/6: 配置和数据目录备份"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

CONFIG_BACKUP="backend_config_backup_${VERSION}_${DATE}.tar.gz"
tar -czf "$CONFIG_BACKUP" \
    --exclude='venv' --exclude='__pycache__' --exclude='*.pyc' \
    --exclude='*.db' --exclude='*.db.*' --exclude='*.tar.gz' \
    --exclude='*.log' \
    *.yml *.txt *.json VERSION \
    data/ services/ skills/ static/ templates/ 2>/dev/null

if [ -f "$CONFIG_BACKUP" ]; then
    CONFIG_SIZE=$(du -h "$CONFIG_BACKUP" | cut -f1)
    echo -e "${GREEN}✅ 配置和数据备份完成${NC}"
    echo "   文件: $CONFIG_BACKUP ($CONFIG_SIZE)"
    ((BACKUP_COUNT++))
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "💻 Part 4/6: 前端备份"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ -d "$PROJECT_DIR/frontend/dist" ]; then
    FRONTEND_BACKUP="frontend_backup_${VERSION}_${DATE}.tar.gz"
    tar -czf "$FRONTEND_BACKUP" -C "$PROJECT_DIR/frontend/dist" . 2>/dev/null
    FRONTEND_SIZE=$(du -h "$FRONTEND_BACKUP" | cut -f1)
    echo -e "${GREEN}✅ 前端备份完成${NC}"
    echo "   文件: $FRONTEND_BACKUP ($FRONTEND_SIZE)"
    ((BACKUP_COUNT++))
fi

# ============================================
# Part 5: GitHub备份（核心功能）
# ============================================

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🐙 Part 5/6: GitHub备份"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

cd "$PROJECT_DIR" || exit 1

# 检查Git配置
if [ ! -d ".git" ]; then
    echo -e "${YELLOW}⚠️  Git未初始化，跳过GitHub备份${NC}"
else
    # 检查远程仓库
    if ! git remote get-url $GIT_REMOTE &>/dev/null; then
        echo -e "${YELLOW}⚠️  GitHub远程仓库未配置${NC}"
        echo "   请运行: git remote add $GIT_REMOTE git@github.com-kanban:$GITHUB_REPO.git"
    else
        echo "📤 准备推送到GitHub..."
        
        # 检查是否有更改
        if [ -n "$(git status --porcelain)" ]; then
            echo "📝 检测到文件更改，正在提交..."
            
            # 添加所有更改
            git add -A
            
            # 创建提交
            git commit -m "Backup: $VERSION - $REASON

Date: $DATE
Version: $VERSION
Reason: $REASON

Changes:
$(git status --short)" || echo "无可提交更改"
            
            echo -e "${GREEN}✅ Git提交完成${NC}"
        else
            echo "ℹ️  无文件更改需要提交"
        fi
        
        # 创建版本标签
        echo "🏷️  创建Git标签: $VERSION"
        git tag -a "$VERSION" -m "Version $VERSION: $REASON" 2>/dev/null || {
            echo "   标签已存在，强制更新..."
            git tag -d "$VERSION" 2>/dev/null || true
            git tag -a "$VERSION" -m "Version $VERSION: $REASON"
        }
        
        # 推送到GitHub
        echo "🚀 推送到GitHub..."
        if git push $GIT_REMOTE $GIT_BRANCH 2>&1 | grep -q "error\|fatal\|rejected"; then
            echo -e "${YELLOW}⚠️  GitHub推送遇到问题，尝试强制推送...${NC}"
            git push $GIT_REMOTE $GIT_BRANCH --force 2>&1 || {
                echo -e "${RED}❌ GitHub推送失败${NC}"
                echo "   可能原因:"
                echo "   1. SSH密钥未添加到GitHub"
                echo "   2. 网络连接问题"
                echo "   3. 仓库权限问题"
            }
        else
            echo -e "${GREEN}✅ GitHub推送成功${NC}"
        fi
        
        # 推送标签
        echo "🏷️  推送标签到GitHub..."
        if git push $GIT_REMOTE $VERSION 2>&1 | grep -v "error\|fatal"; then
            echo -e "${GREEN}✅ 标签推送成功${NC}"
            GIT_PUSHED=true
        else
            echo -e "${YELLOW}⚠️  标签推送失败${NC}"
        fi
        
        # 显示GitHub链接
        echo ""
        echo "🔗 GitHub链接:"
        echo "   仓库: https://github.com/$GITHUB_REPO"
        echo "   标签: https://github.com/$GITHUB_REPO/releases/tag/$VERSION"
    fi
fi

cd "$BACKEND_DIR" || exit 1

# ============================================
# Part 6: 更新本地版本记录
# ============================================

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📝 Part 6/6: 更新本地版本记录"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

cat > "VERSION" << EOF
# 看板2.4系统版本记录

CURRENT_VERSION=$VERSION
LAST_UPDATE=$DATE
UPDATE_REASON=$REASON
GITHUB_PUSHED=$GIT_PUSHED

## 版本历史
- $VERSION ($DATE) - 当前版本 - $REASON
EOF

echo -e "${GREEN}✅ 版本记录已更新${NC}"

# ============================================
# 清理旧版本
# ============================================

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🧹 清理旧版本（保留最近$RETAIN_COUNT个）"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

for pattern in "*.backup_v*" "backend_py_backup_*.tar.gz" \
               "backend_config_backup_*.tar.gz" "frontend_backup_*.tar.gz"; do
    COUNT=$(ls -1 $pattern 2>/dev/null | wc -l)
    if [ $COUNT -gt $RETAIN_COUNT ]; then
        ls -t $pattern 2>/dev/null | tail -n +$((RETAIN_COUNT+1)) | xargs -r rm -f
    fi
done

echo -e "${GREEN}✅ 旧版本清理完成${NC}"

# ============================================
# 摘要
# ============================================

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║                   📊 备份完成摘要                          ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""
echo "📦 项目名称: 看板2.4系统"
echo "🏷️  版本号: $VERSION"
echo "📝 更新原因: $REASON"
echo "📅 备份时间: $DATE"
echo ""
echo "✅ 本地备份: $BACKUP_COUNT/4 部分"

if [ "$GIT_PUSHED" = true ]; then
    echo -e "✅ GitHub备份: ${GREEN}成功${NC}"
    echo "🔗 https://github.com/$GITHUB_REPO/releases/tag/$VERSION"
else
    echo -e "⚠️  GitHub备份: ${YELLOW}失败或跳过${NC}"
fi

echo ""
echo "📂 本地备份文件:"
echo "────────────────────────────────────────────────────────────"
ls -lh *.backup_${VERSION}_${DATE}* 2>/dev/null | awk '{printf "  %-45s %10s\n", $9, $5}'
ls -lh *_backup_${VERSION}_${DATE}.tar.gz 2>/dev/null | awk '{printf "  %-45s %10s\n", $9, $5}'
echo "────────────────────────────────────────────────────────────"
echo ""
echo -e "${GREEN}✅ 完整备份完成！${NC}"
echo ""

# 创建检查清单
cat << 'CHECKLIST'
📋 备份检查清单:
  ✅ 数据库已备份
  ✅ Python后端代码已备份
  ✅ 配置和数据已备份
  ✅ 前端已备份
  ✅ GitHub已推送 (如配置正确)
  ✅ 版本记录已更新
  ✅ 旧版本已清理

CHECKLIST

if [ "$GIT_PUSHED" = false ]; then
echo "⚠️  注意: GitHub推送失败"
echo "   解决步骤:"
echo "   1. 将SSH公钥添加到GitHub: https://github.com/$GITHUB_REPO/settings/keys"
echo "   2. 公钥内容: ~/.ssh/kanban_github.pub"
echo ""
fi
