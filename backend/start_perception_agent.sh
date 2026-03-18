#!/bin/bash
#
# 感知 Agent 启动脚本
# 用于 systemd 服务或手动启动
#

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 路径配置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

LOG_FILE="$SCRIPT_DIR/perception_agent.log"
PID_FILE="$SCRIPT_DIR/perception_agent.pid"
CONFIG_FILE="$SCRIPT_DIR/perception_config.yml"
VENV_DIR="$SCRIPT_DIR/venv"

# 日志函数
log() {
    local level=$1
    shift
    local message="$@"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${timestamp} [${level}] ${message}" | tee -a "$LOG_FILE"
}

log_info() {
    log "INFO" "$@"
}

log_error() {
    log "ERROR" "$@"
}

log_warn() {
    log "WARN" "$@"
}

# 检查 Python 环境
check_python() {
    if [ -d "$VENV_DIR" ]; then
        # 使用虚拟环境
        PYTHON="$VENV_DIR/bin/python3"
        PIP="$VENV_DIR/bin/pip"
        log_info "使用虚拟环境：$VENV_DIR"
    else
        # 使用系统 Python
        PYTHON="python3"
        PIP="pip3"
        log_info "使用系统 Python"
    fi
    
    # 检查 Python 版本
    if ! command -v $PYTHON &> /dev/null; then
        log_error "Python3 未安装"
        exit 1
    fi
    
    log_info "Python 版本：$($PYTHON --version)"
}

# 检查依赖
check_dependencies() {
    log_info "检查依赖..."
    
    # 检查必需的 Python 包
    REQUIRED_PACKAGES="flask pyyaml"
    
    for package in $REQUIRED_PACKAGES; do
        if ! $PYTHON -c "import $(echo $package | tr '-' '_')" 2>/dev/null; then
            log_warn "缺少依赖包：$package，尝试安装..."
            if [ -d "$VENV_DIR" ]; then
                $PIP install -q $package
            else
                $PIP install --break-system-packages -q $package
            fi
        fi
    done
    
    log_info "依赖检查完成"
}

# 检查配置文件
check_config() {
    if [ ! -f "$CONFIG_FILE" ]; then
        log_warn "配置文件不存在：$CONFIG_FILE"
        log_info "创建默认配置文件..."
        cat > "$CONFIG_FILE" << 'EOF'
# 感知 Agent 配置文件
agent:
  name: "感知 Agent"
  version: "1.0.0"
  enabled: true
  
database:
  path: "./kanban_v5.db"
  
monitoring:
  enabled: true
  check_interval: 60  # 秒
  
user_behavior:
  enabled: true
  record_actions: true
  
system:
  enabled: true
  check_resources: true
  
logging:
  level: "INFO"
  file: "./perception_agent.log"
EOF
        log_info "默认配置文件已创建"
    else
        log_info "配置文件已存在：$CONFIG_FILE"
    fi
}

# 检查数据库表
check_database() {
    log_info "检查数据库表..."
    
    $PYTHON << 'PYEOF'
import sqlite3
import os

db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'kanban_v5.db')

if not os.path.exists(db_path):
    print(f"❌ 数据库文件不存在：{db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# 检查 perception_events 表
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='perception_events'")
if cursor.fetchone():
    print("✅ perception_events 表已存在")
else:
    print("❌ perception_events 表不存在，运行 init_perception_db.py 创建")
    exit(1)

conn.close()
PYEOF
    
    if [ $? -ne 0 ]; then
        log_info "初始化数据库表..."
        $PYTHON init_perception_db.py
    fi
}

# 启动感知 Agent
start_agent() {
    log_info "启动感知 Agent..."
    
    # 检查是否已经在运行
    if [ -f "$PID_FILE" ]; then
        OLD_PID=$(cat "$PID_FILE")
        if kill -0 $OLD_PID 2>/dev/null; then
            log_warn "感知 Agent 已经在运行 (PID: $OLD_PID)"
            return 1
        else
            log_warn "发现遗留的 PID 文件，删除它"
            rm -f "$PID_FILE"
        fi
    fi
    
    # 启动进程
    nohup $PYTHON perception_agent.py > "$LOG_FILE" 2>&1 &
    PID=$!
    
    echo $PID > "$PID_FILE"
    
    sleep 2
    
    # 检查是否成功启动
    if kill -0 $PID 2>/dev/null; then
        log_info "✅ 感知 Agent 启动成功 (PID: $PID)"
        return 0
    else
        log_error "❌ 感知 Agent 启动失败"
        rm -f "$PID_FILE"
        return 1
    fi
}

# 停止感知 Agent
stop_agent() {
    log_info "停止感知 Agent..."
    
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 $PID 2>/dev/null; then
            kill $PID
            sleep 2
            if kill -0 $PID 2>/dev/null; then
                log_warn "强制终止进程..."
                kill -9 $PID
            fi
            log_info "✅ 感知 Agent 已停止"
        else
            log_warn "进程未运行"
        fi
        rm -f "$PID_FILE"
    else
        log_warn "PID 文件不存在，尝试查找进程..."
        pkill -f "perception_agent.py" || true
    fi
}

# 重启感知 Agent
restart_agent() {
    stop_agent
    sleep 2
    start_agent
}

# 查看状态
status_agent() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if kill -0 $PID 2>/dev/null; then
            echo -e "${GREEN}✅ 感知 Agent 正在运行 (PID: $PID)${NC}"
            return 0
        else
            echo -e "${YELLOW}⚠️  进程未运行 (残留 PID 文件)${NC}"
            return 1
        fi
    else
        echo -e "${RED}❌ 感知 Agent 未运行${NC}"
        return 1
    fi
}

# 查看日志
tail_logs() {
    if [ -f "$LOG_FILE" ]; then
        tail -f "$LOG_FILE"
    else
        log_error "日志文件不存在：$LOG_FILE"
        exit 1
    fi
}

# 显示帮助
show_help() {
    echo "感知 Agent 启动脚本"
    echo ""
    echo "用法：$0 {start|stop|restart|status|logs|check}"
    echo ""
    echo "命令:"
    echo "  start    启动感知 Agent"
    echo "  stop     停止感知 Agent"
    echo "  restart  重启感知 Agent"
    echo "  status   查看运行状态"
    echo "  logs     查看日志 (实时)"
    echo "  check    运行前检查"
    echo "  help     显示帮助"
    echo ""
}

# 主函数
main() {
    case "$1" in
        start)
            check_python
            check_dependencies
            check_config
            check_database
            start_agent
            ;;
        stop)
            stop_agent
            ;;
        restart)
            restart_agent
            ;;
        status)
            status_agent
            ;;
        logs)
            tail_logs
            ;;
        check)
            check_python
            check_dependencies
            check_config
            check_database
            echo ""
            log_info "✅ 所有检查通过"
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            # 默认：启动
            check_python
            check_dependencies
            check_config
            check_database
            start_agent
            ;;
    esac
}

# 执行
main "$@"
