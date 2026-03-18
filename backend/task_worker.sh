#!/bin/bash
# T109 MacMini 任务轮询服务 - 快速启动脚本

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 显示帮助
show_help() {
    cat << EOF
T109 MacMini 任务轮询服务 - 快速启动脚本

用法：$0 [选项]

选项:
    start       启动生产服务（需要 SLURM）
    start-sim   启动模拟服务（无需 SLURM）
    stop        停止服务
    status      查看服务状态
    test        运行测试
    migrate     执行数据库迁移
    once        执行单轮任务
    logs        查看实时日志
    clean       清理旧日志和输出
    help        显示此帮助信息

示例:
    $0 start        # 启动生产服务
    $0 start-sim    # 启动模拟服务（测试用）
    $0 migrate      # 首次使用时执行
    $0 logs         # 查看实时日志
    $0 status       # 查看服务状态

EOF
}

# 检查 Python
check_python() {
    if ! command -v python3 &> /dev/null; then
        print_error "Python3 未安装"
        exit 1
    fi
    
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    print_info "Python 版本：$PYTHON_VERSION"
}

# 检查数据库
check_database() {
    if [ ! -f "kanban_v5.db" ]; then
        print_warning "数据库文件不存在：kanban_v5.db"
        return 1
    fi
    print_info "数据库：存在"
    return 0
}

# 检查 SLURM
check_slurm() {
    if command -v sbatch &> /dev/null; then
        print_info "SLURM: 已安装"
        return 0
    else
        print_warning "SLURM: 未安装（将使用模拟模式）"
        return 1
    fi
}

# 数据库迁移
do_migrate() {
    print_info "执行数据库迁移..."
    if [ -f "migrate_task_worker.py" ]; then
        python3 migrate_task_worker.py
        print_success "数据库迁移完成"
    else
        print_error "迁移脚本不存在：migrate_task_worker.py"
        exit 1
    fi
}

# 启动生产服务
do_start() {
    check_python
    check_database || exit 1
    
    print_info "启动生产服务..."
    print_warning "需要 SLURM 环境"
    
    if ! check_slurm; then
        print_error "SLURM 未安装，无法启动生产服务"
        print_info "请使用：$0 start-sim（模拟模式）"
        exit 1
    fi
    
    # 创建日志目录
    mkdir -p logs slurm_output
    
    # 启动服务
    python3 task_worker.py --start
}

# 启动模拟服务
do_start_sim() {
    check_python
    check_database || exit 1
    
    print_info "启动模拟服务（无需 SLURM）..."
    
    # 创建日志和输出目录
    mkdir -p logs sim_output
    
    # 启动服务
    python3 task_worker_sim.py --start
}

# 停止服务
do_stop() {
    print_info "停止服务..."
    
    # 查找并终止进程
    PIDS=$(pgrep -f "task_worker.py" || true)
    
    if [ -n "$PIDS" ]; then
        echo "$PIDS" | xargs kill
        print_success "服务已停止"
    else
        print_info "服务未运行"
    fi
}

# 查看状态
do_status() {
    print_info "服务状态检查"
    echo "===================="
    
    # 检查进程
    if pgrep -f "task_worker.py" > /dev/null; then
        print_success "服务状态：运行中"
        pgrep -af "task_worker.py"
    else
        print_warning "服务状态：未运行"
    fi
    
    echo ""
    
    # 检查数据库
    if check_database; then
        # 统计任务
        print_info "任务统计:"
        sqlite3 kanban_v5.db <<EOF
.mode column
.headers on
SELECT 
    status AS '状态',
    COUNT(*) AS '数量'
FROM tasks 
GROUP BY status
ORDER BY 
    CASE status
        WHEN 'todo' THEN 1
        WHEN 'in_progress' THEN 2
        WHEN 'running' THEN 3
        WHEN 'completed' THEN 4
        WHEN 'failed' THEN 5
        ELSE 6
    END;
EOF
    fi
    
    echo ""
    
    # 检查 SLURM
    if check_slurm; then
        print_info "SLURM 作业:"
        squeue -u $USER -h | head -10 || print_info "无运行中的作业"
    fi
}

# 运行测试
do_test() {
    print_info "运行测试..."
    
    check_python
    check_database || exit 1
    
    python3 task_worker.py --test
}

# 执行单轮
do_once() {
    print_info "执行单轮任务处理..."
    
    check_python
    check_database || exit 1
    
    if check_slurm; then
        python3 task_worker.py --once
    else
        python3 task_worker_sim.py --once
    fi
}

# 查看日志
do_logs() {
    TODAY=$(date +%Y%m%d)
    LOG_FILE="logs/task_worker_${TODAY}.log"
    LOG_FILE_SIM="logs/task_worker_sim_${TODAY}.log"
    
    print_info "查看实时日志..."
    
    if [ -f "$LOG_FILE" ]; then
        tail -f "$LOG_FILE"
    elif [ -f "$LOG_FILE_SIM" ]; then
        tail -f "$LOG_FILE_SIM"
    else
        print_warning "今日日志文件不存在"
        print_info "可用日志:"
        ls -lt logs/*.log 2>/dev/null | head -10 || print_info "无日志文件"
    fi
}

# 清理
do_clean() {
    print_info "清理旧文件..."
    
    # 清理 30 天前的日志
    find logs/ -name "*.log" -mtime +30 -delete 2>/dev/null || true
    print_success "已清理旧日志"
    
    # 清理 7 天前的输出
    find slurm_output/ -name "*.out" -mtime +7 -delete 2>/dev/null || true
    find slurm_output/ -name "*.err" -mtime +7 -delete 2>/dev/null || true
    find sim_output/ -name "*.out" -mtime +7 -delete 2>/dev/null || true
    find sim_output/ -name "*.err" -mtime +7 -delete 2>/dev/null || true
    find sim_output/ -name "*.sh" -mtime +7 -delete 2>/dev/null || true
    print_success "已清理旧输出文件"
}

# 主函数
main() {
    case "${1:-help}" in
        start)
            do_start
            ;;
        start-sim)
            do_start_sim
            ;;
        stop)
            do_stop
            ;;
        status)
            do_status
            ;;
        test)
            do_test
            ;;
        migrate)
            do_migrate
            ;;
        once)
            do_once
            ;;
        logs)
            do_logs
            ;;
        clean)
            do_clean
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            print_error "未知选项：$1"
            show_help
            exit 1
            ;;
    esac
}

main "$@"
