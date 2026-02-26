#!/bin/bash
# 部署 kanban-react 到 kanban1.mettlyz.com

echo "=============================================="
echo "部署看板系统 React 版本"
echo "=============================================="
echo ""

# 1. 安装前端依赖
echo "📦 安装前端依赖..."
cd frontend
npm install

# 2. 构建前端
echo "🔨 构建前端..."
npm run build

# 3. 复制构建文件到后端
echo "📂 复制构建文件..."
cp -r build ../backend/

# 4. 启动后端服务
echo "🚀 启动后端服务..."
cd ../backend

# 检查是否已有进程在运行
pkill -f "kanban-react/backend/app.py" 2>/dev/null

# 使用 nohup 后台运行
nohup python3 app.py > ../server.log 2>&1 &

echo ""
echo "=============================================="
echo "✅ 部署完成！"
echo "=============================================="
echo ""
echo "访问地址:"
echo "  - 本地: http://localhost:8086"
echo "  - 域名: https://kanban1.mettlyz.com"
echo ""
echo "查看日志:"
echo "  tail -f ~/.openclaw/workspace/kanban-react/server.log"
echo ""
