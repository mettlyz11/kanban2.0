#!/bin/bash
# full_backup_with_version.sh - 完整备份并记录版本

VERSION=${1:-"v2.4.x"}
REASON=${2:-"常规更新"}
DATE=$(date +%Y%m%d_%H%M%S)
BACKEND_DIR="/opt/kanban-react/backend"
FRONTEND_DIR="/opt/kanban-react/frontend"

echo "🚀 开始完整备份 (${VERSION}_${DATE})..."
echo "   更新原因: $REASON"

# Part 1: 数据库
echo "[1/5] 备份数据库..."
cp "${BACKEND_DIR}/kanban_v5.db"    "${BACKEND_DIR}/kanban_v5.db.backup_${VERSION}_${DATE}"
echo "   ✅ 数据库备份完成"

# Part 2: 后端Python代码
echo "[2/5] 备份后端Python代码..."
tar -czf "${BACKEND_DIR}/backend_py_backup_${VERSION}_${DATE}.tar.gz"     -C "${BACKEND_DIR}"     --exclude='venv' --exclude='__pycache__' --exclude='*.pyc'     *.py 2>/dev/null
echo "   ✅ Python代码备份完成"

# Part 3: 后端配置和数据
echo "[3/5] 备份后端配置和数据..."
tar -czf "${BACKEND_DIR}/backend_config_backup_${VERSION}_${DATE}.tar.gz"     -C "${BACKEND_DIR}"     --exclude='venv' --exclude='__pycache__' --exclude='*.pyc'     --exclude='*.db' --exclude='*.db.*' --exclude='*.tar.gz'     --exclude='*.log'     *.yml *.txt *.sql *.sh VERSION     data/ services/ skills/ static/ templates/ 2>/dev/null
echo "   ✅ 配置和数据备份完成"

# Part 4: 前端
echo "[4/5] 备份前端..."
tar -czf "${BACKEND_DIR}/frontend_backup_${VERSION}_${DATE}.tar.gz"     -C "${FRONTEND_DIR}/dist" . 2>/dev/null
echo "   ✅ 前端备份完成"

# Part 5: 更新版本记录
echo "[5/5] 更新版本记录..."
"${BACKEND_DIR}/update_version.sh" "$VERSION" "$REASON"
echo "   ✅ 版本记录更新完成"

# 清理旧版本
echo "清理旧版本..."
for pattern in "*.backup_v2.4.*" "backend_py_backup_*.tar.gz"                "backend_config_backup_*.tar.gz" "frontend_backup_*.tar.gz"; do
    ls -t ${BACKEND_DIR}/${pattern} 2>/dev/null | tail -n +21 | xargs -r rm -f
done
echo "   ✅ 旧版本清理完成"

echo ""
echo "✅ 完整备份完成: ${VERSION}_${DATE}"
echo ""
echo "📋 备份清单:"
ls -lh ${BACKEND_DIR}/*backup_${VERSION}_${DATE}* 2>/dev/null | awk '{print "  " $9 " (" $5 ")"}'
echo ""
echo "📝 当前版本: $VERSION"
echo "📝 更新原因: $REASON"
