#!/bin/bash
# 开发模式启动

echo "🚀 启动开发服务器..."
echo ""

# 启动后端 (在后台)
echo "📡 启动 Flask 后端 (端口 8086)..."
cd backend
python3 app.py &
BACKEND_PID=$!

# 等待后端启动
sleep 2

# 启动前端 (在新窗口或后台)
echo "⚛️  启动 React 前端..."
cd ../frontend
npm start &
FRONTEND_PID=$!

echo ""
echo "=============================================="
echo "✅ 开发服务器已启动！"
echo "=============================================="
echo ""
echo "访问地址:"
echo "  前端: http://localhost:3000"
echo "  后端: http://localhost:8086"
echo ""
echo "按 Ctrl+C 停止所有服务"
echo ""

# 捕获退出信号
function cleanup {
    echo ""
    echo "🛑 停止服务..."
    kill $BACKEND_PID 2>/dev/null
    kill $FRONTEND_PID 2>/dev/null
    exit
}
trap cleanup INT

# 保持脚本运行
wait
