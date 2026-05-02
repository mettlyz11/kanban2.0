#!/bin/bash
#
# 看板系统自动健康检查脚本
# 服务器: 47.93.184.128
# 任务ID: 328
#

# 配置信息
SERVER_IP="47.93.184.128"
SSH_USER="root"
SSH_KEY_PATH="/Users/mettlyz/.openclaw/workspace/info/aliserver1.pem"
LOG_FILE="/Users/mettlyz/.openclaw/workspace/logs/kanban-health-check.log"
ALERT_WEBHOOK=""  # 可配置Telegram/Feishu告警webhook
SSH_TIMEOUT=30

# 阈值配置
CPU_WARN_THRESHOLD=80
CPU_CRIT_THRESHOLD=95
MEM_WARN_THRESHOLD=85
MEM_CRIT_THRESHOLD=95
DISK_WARN_THRESHOLD=80
DISK_CRIT_THRESHOLD=90

# 创建日志目录
mkdir -p "$(dirname "$LOG_FILE")"

# 日志函数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# 告警函数
alert() {
    local message="$1"
    log "⚠️ ALERT: $message"
    # 如果配置了webhook，可以发送告警
    if [ -n "$ALERT_WEBHOOK" ]; then
        curl -s -X POST "$ALERT_WEBHOOK" -d "text=$message" > /dev/null
    fi
}

# 检查SSH连接
check_ssh() {
    log "🔍 Checking SSH connection to $SERVER_IP..."
    ssh -i "$SSH_KEY_PATH" -o ConnectTimeout=$SSH_TIMEOUT -o BatchMode=yes -o StrictHostKeyChecking=no "$SSH_USER@$SERVER_IP" "echo OK" >/dev/null 2>&1
    if [ $? -eq 0 ]; then
        log "✅ SSH connection successful"
        return 0
    else
        alert "SSH connection to $SERVER_IP FAILED"
        return 1
    fi
}

# 获取系统资源使用情况
check_system_resources() {
    log "🔍 Checking system resources..."
    
    # 使用 mpstat 获取CPU使用率，更可靠
    if ssh -i "$SSH_KEY_PATH" "$SSH_USER@$SERVER_IP" "which mpstat > /dev/null 2>&1"; then
        local cpu_idle=$(ssh -i "$SSH_KEY_PATH" "$SSH_USER@$SERVER_IP" "mpstat 1 1 | tail -n 1 | awk '{print \$NF}'")
        local cpu_usage=$(echo "$cpu_idle" | awk '{printf "%d", 100 - $1}')
    else
        # 回退到top命令方式
        local cpu_usage=$(ssh -i "$SSH_KEY_PATH" "$SSH_USER@$SERVER_IP" "ps -aux --sort=-%cpu | head -n 10 | awk '{sum+=$3} END {print int(sum)}'")
    fi
    
    local mem_info=$(ssh -i "$SSH_KEY_PATH" "$SSH_USER@$SERVER_IP" "free | grep Mem")
    local mem_total=$(echo "$mem_info" | awk '{print $2}')
    local mem_used=$(echo "$mem_info" | awk '{print $3}')
    local mem_usage=$(( mem_used * 100 / mem_total ))
    local disk_usage=$(ssh -i "$SSH_KEY_PATH" "$SSH_USER@$SERVER_IP" "df -h / | grep / | awk '{print \$5}' | sed 's/%//g'")
    
    # 处理空值
    if [ -z "$cpu_usage" ] || [ "$cpu_usage" = "" ]; then
        cpu_usage=0
    fi
    if [ -z "$disk_usage" ] || [ "$disk_usage" = "" ]; then
        disk_usage=0
    fi
    
    log "CPU Usage: ${cpu_usage}%, Memory Usage: ${mem_usage}%, Disk Usage: ${disk_usage}%"
    
    # CPU检查
    if [ "$cpu_usage" -ge "$CPU_CRIT_THRESHOLD" ]; then
        alert "CRITICAL: CPU usage is ${cpu_usage}% on $SERVER_IP"
    elif [ "$cpu_usage" -ge "$CPU_WARN_THRESHOLD" ]; then
        alert "WARNING: CPU usage is ${cpu_usage}% on $SERVER_IP"
    fi
    
    # 内存检查
    if [ "$mem_usage" -ge "$MEM_CRIT_THRESHOLD" ]; then
        alert "CRITICAL: Memory usage is ${mem_usage}% on $SERVER_IP"
    elif [ "$mem_usage" -ge "$MEM_WARN_THRESHOLD" ]; then
        alert "WARNING: Memory usage is ${mem_usage}% on $SERVER_IP"
    fi
    
    # 磁盘检查
    if [ "$disk_usage" -ge "$DISK_CRIT_THRESHOLD" ]; then
        alert "CRITICAL: Disk usage is ${disk_usage}% on $SERVER_IP"
    elif [ "$disk_usage" -ge "$DISK_WARN_THRESHOLD" ]; then
        alert "WARNING: Disk usage is ${disk_usage}% on $SERVER_IP"
    fi
}

# 检查关键进程
check_processes() {
    log "🔍 Checking critical processes..."
    
    # 实际运行的关键进程（看板系统是Python应用，gunicorn由python3运行）
    local processes=("nginx" "supervisord" "dockerd")
    
    for proc in "${processes[@]}"; do
        if ssh -i "$SSH_KEY_PATH" "$SSH_USER@$SERVER_IP" "pgrep -x $proc > /dev/null 2>&1 || pgrep $proc > /dev/null 2>&1"; then
            log "✅ Process $proc is running"
        else
            alert "Process $proc is NOT running on $SERVER_IP"
        fi
    done
    
    # 检查gunicorn/python进程 - 看板后端应用
    local gunicorn_count=$(ssh -i "$SSH_KEY_PATH" "$SSH_USER@$SERVER_IP" "ps aux | grep -c gunicorn")
    if [ "$gunicorn_count" -gt 1 ]; then  # grep本身也计数一次
        log "✅ gunicorn (kanban backend) is running"
    else
        alert "gunicorn (kanban backend) is NOT running on $SERVER_IP"
    fi
}

# 检查HTTP服务
check_http() {
    log "🔍 Checking HTTP service..."
    
    # 目前只配置了HTTP，HTTPS未配置
    local urls=("http://$SERVER_IP")
    
    for url in "${urls[@]}"; do
        local status_code=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 "$url")
        if [ "$status_code" = "200" ]; then
            log "✅ $url returned $status_code"
        elif [ "$status_code" = "301" ] || [ "$status_code" = "302" ]; then
            log "➡️  $url returned $status_code (redirect)"
        else
            alert "$url returned unexpected status code: $status_code"
        fi
    done
    
    # 也检查一下后端API端口
    local api_url="http://$SERVER_IP:8086"
    local api_status=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 "$api_url")
    if [ "$api_status" = "200" ] || [ "$api_status" = "404" ] || [ "$api_status" = "301" ] || [ "$api_status" = "302" ]; then
        # 404说明服务在运行只是路径不对，也算正常
        log "✅ Backend API $api_url is responding (status: $api_status)"
    else
        alert "Backend API $api_url not responding (status: $api_status)"
    fi
}

# 检查最近的错误日志
check_error_logs() {
    log "🔍 Checking recent error logs (last 100 lines)..."
    
    # 检查NGINX错误日志，路径根据实际情况调整
    local error_count=$(ssh -i "$SSH_KEY_PATH" "$SSH_USER@$SERVER_IP" "tail -n 100 /var/log/nginx/error.log 2>/dev/null | grep -i 'error\|crit\|alert' | wc -l")
    
    if [ "$error_count" -gt 0 ]; then
        alert "Found $error_count error(s) in nginx error log recently"
        # 输出最近5个错误到本地日志
        log "Recent errors:"
        ssh -i "$SSH_KEY_PATH" "$SSH_USER@$SERVER_IP" "tail -n 100 /var/log/nginx/error.log 2>/dev/null | grep -i 'error\|crit\|alert' | tail -5" | tee -a "$LOG_FILE"
    else
        log "✅ No recent errors found in nginx error log"
    fi
}

# 主函数
main() {
    log "========================================"
    log "Starting Kanban system health check"
    log "Server: $SERVER_IP"
    log "========================================"
    
    # 第一步：检查SSH连接
    if ! check_ssh; then
        log "❌ SSH check failed, aborting further checks"
        log "Health check completed with ERRORS"
        log "========================================"
        exit 1
    fi
    
    # 第二步：系统资源检查
    check_system_resources
    
    # 第三步：进程检查
    check_processes
    
    # 第四步：HTTP服务检查
    check_http
    
    # 第五步：错误日志检查（只在每天完整检查时执行）
    if [ "$1" = "full" ]; then
        check_error_logs
    fi
    
    log "========================================"
    log "Health check completed"
    log "========================================"
    echo ""
}

# 显示帮助
show_help() {
    echo "Kanban System Health Check Script"
    echo ""
    echo "Usage:"
    echo "  ./kanban-health-check.sh [options]"
    echo ""
    echo "Options:"
    echo "  quick   Quick check (SSH, resources, processes, HTTP) - default"
    echo "  full    Full check including error logs"
    echo "  help    Show this help"
    echo ""
}

# 入口
case "${1:-quick}" in
    quick)
        main "quick"
        ;;
    full)
        main "full"
        ;;
    help)
        show_help
        ;;
    *)
        echo "Unknown option: $1"
        show_help
        exit 1
        ;;
esac
