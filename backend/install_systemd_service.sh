#!/bin/bash
#
# 感知 Agent systemd 服务安装脚本
#

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}感知 Agent systemd 服务安装脚本${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# 检查是否是 root 用户
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}❌ 请使用 sudo 运行此脚本${NC}"
    echo "用法：sudo ./install_systemd_service.sh"
    exit 1
fi

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_FILE="$SCRIPT_DIR/perception-agent.service"

echo -e "${YELLOW}📂 工作目录：$SCRIPT_DIR${NC}"
echo ""

# 检查服务文件是否存在
if [ ! -f "$SERVICE_FILE" ]; then
    echo -e "${RED}❌ 服务文件不存在：$SERVICE_FILE${NC}"
    exit 1
fi

# 更新服务文件中的路径
echo -e "${YELLOW}📝 配置服务文件路径...${NC}"
cat > /etc/systemd/system/perception-agent.service << EOF
[Unit]
Description=感知 Agent 系统 (Perception Agent)
Documentation=https://github.com/mettlyz11/kanban-system
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$SCRIPT_DIR
ExecStart=/usr/bin/python3 $SCRIPT_DIR/start_perception_agent.sh
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=perception-agent

# 环境变量
Environment="PYTHONUNBUFFERED=1"
Environment="PATH=/usr/local/bin:/usr/bin:/bin"

# 安全设置
NoNewPrivileges=false
PrivateTmp=true

[Install]
WantedBy=multi-user.target
EOF

echo -e "${GREEN}✅ 服务文件已安装到 /etc/systemd/system/perception-agent.service${NC}"
echo ""

# 重新加载 systemd
echo -e "${YELLOW}🔄 重新加载 systemd 配置...${NC}"
systemctl daemon-reload

# 启用服务（开机自启）
echo -e "${YELLOW}⚙️  启用开机自启...${NC}"
systemctl enable perception-agent.service

echo -e "${GREEN}✅ 服务已启用${NC}"
echo ""

# 启动服务
echo -e "${YELLOW}🚀 启动感知 Agent 服务...${NC}"
systemctl start perception-agent.service

# 等待服务启动
sleep 3

# 检查服务状态
echo ""
echo -e "${YELLOW}📊 服务状态：${NC}"
systemctl status perception-agent.service --no-pager

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}安装完成！${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "常用命令:"
echo -e "  ${YELLOW}systemctl start perception-agent${NC}      - 启动服务"
echo -e "  ${YELLOW}systemctl stop perception-agent${NC}       - 停止服务"
echo -e "  ${YELLOW}systemctl restart perception-agent${NC}    - 重启服务"
echo -e "  ${YELLOW}systemctl status perception-agent${NC}     - 查看状态"
echo -e "  ${YELLOW}journalctl -u perception-agent -f${NC}     - 查看日志"
echo -e "  ${YELLOW}systemctl disable perception-agent${NC}    - 禁用开机自启"
echo ""
