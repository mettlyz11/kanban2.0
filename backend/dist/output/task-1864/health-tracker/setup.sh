#!/bin/bash
set -e

echo "🚀 Health Tracker 安装脚本"
echo "==========================="

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "❌ 未检测到 Python3，请先安装"
    exit 1
fi

echo "✅ Python3 已安装: $(python3 --version)"

# 检查 Docker
if ! command -v docker &> /dev/null; then
    echo "⚠️ 未检测到 Docker，请先安装 Docker Desktop"
    echo "   下载地址: https://www.docker.com/products/docker-desktop"
    exit 1
fi

echo "✅ Docker 已安装"

# 创建虚拟环境
echo "📦 创建 Python 虚拟环境..."
python3 -m venv venv
source venv/bin/activate

# 安装依赖
echo "📦 安装 Python 依赖..."
pip install --upgrade pip
pip install -r requirements.txt

# 复制配置文件
if [ ! -f "config.local.yaml" ]; then
    echo "📝 创建本地配置文件..."
    cp config.yaml config.local.yaml
    echo "⚠️ 请编辑 config.local.yaml 填入你的 InfluxDB Token 和企业微信 Webhook"
fi

# 创建目录
mkdir -p reports logs

# 启动基础设施
echo "🐳 启动 InfluxDB + Grafana..."
docker-compose up -d

# 等待 InfluxDB 启动
echo "⏳ 等待 InfluxDB 启动..."
sleep 10

# 测试连接
echo "🔍 测试数据库连接..."
python3 -c "
from influxdb_client import InfluxDBClient
try:
    client = InfluxDBClient(url='http://localhost:8086', token='health-tracker-token-2026', org='personal')
    client.ping()
    print('✅ InfluxDB 连接成功')
except Exception as e:
    print(f'⚠️ InfluxDB 连接失败: {e}')
"

echo ""
echo "🎉 安装完成！"
echo "=================="
echo ""
echo "📊 Grafana 仪表盘: http://localhost:3000"
echo "   账号: admin / admin"
echo ""
echo "📋 下一步操作:"
echo "   1. 编辑 config.local.yaml 配置"
echo "   2. 从 iPhone 导出 Apple Health 数据（或保持模拟模式）"
echo "   3. 运行测试: python main.py sync"
echo "   4. 配置 cron 定时任务"
echo ""
echo "📖 详细文档请查看 README.md"
