#!/bin/bash
# 启动看板系统 v2.0 (React版) - 完整启动脚本

echo "═══════════════════════════════════════════════════════════"
echo "        🚀 启动看板系统 v2.0 (React + Flask)"
echo "═══════════════════════════════════════════════════════════"
echo ""

# 获取本机IP
LOCAL_IP=$(ifconfig | grep "inet " | grep -v 127.0.0.1 | head -1 | awk '{print $2}')
echo "📍 本机IP: $LOCAL_IP"
echo ""

# 停止旧服务
echo "🛑 停止旧服务..."
pkill -f "kanban-react/backend/app.py" 2>/dev/null
sleep 1

# 启动后端
echo "📡 启动 Flask 后端 (端口8086)..."
cd ~/.openclaw/workspace/kanban-react/backend
python3 app.py > ../server.log 2>&1 &
BACKEND_PID=$!
sleep 2

# 检查后端是否启动
if curl -s http://localhost:8086/api/stats > /dev/null; then
    echo "✅ 后端启动成功 (PID: $BACKEND_PID)"
else
    echo "❌ 后端启动失败"
    exit 1
fi

echo ""
echo "═══════════════════════════════════════════════════════════"
echo "                   ✅ 启动成功！"
echo "═══════════════════════════════════════════════════════════"
echo ""
echo "🌐 访问方式 (任选其一):"
echo ""
echo "1️⃣  本地访问:"
echo "    http://localhost:8086"
echo ""
echo "2️⃣  局域网访问 (同一WiFi内其他设备):"
echo "    http://$LOCAL_IP:8086"
echo ""
echo "3️⃣  配置域名访问 (需要手动执行):"
echo "    sudo sh -c 'echo \"127.0.0.1 kanban1.mettlyz.com\" >> /etc/hosts'"
echo "    然后访问: http://kanban1.mettlyz.com"
echo ""
echo "📊 API测试:"
echo "    curl http://localhost:8086/api/stats"
echo ""
echo "📝 查看日志:"
echo "    tail -f ~/.openclaw/workspace/kanban-react/server.log"
echo ""
echo "🛑 停止服务:"
echo "    pkill -f 'kanban-react/backend/app.py'"
echo ""
echo "═══════════════════════════════════════════════════════════"

# 保存PID到文件
echo $BACKEND_PID > ~/.openclaw/workspace/kanban-react/server.pid

# 保持脚本运行
wait
