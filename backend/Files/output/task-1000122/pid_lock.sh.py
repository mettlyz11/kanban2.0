# pid_lock.sh

> 任务: v5 #1 PID 文件锁 — 防重复启动
> 附件类型: 代码文件 (Shell脚本)
> 生成时间: 2026-05-11 21:13

```bash
#!/bin/env bash
#=======================================================================
# 文件:       pid_lock.sh
# 作者:       GPT-4 (自动生成)
# 版本:       1.0
# 创建日期:   2025-03-21
# 用途:       实现PID文件锁机制，防止同一进程重复启动。
#              该脚本通过检查PID文件是否存在且进程存活来判定，
#              在启动时创建PID文件，在终止（正常退出、SIGTERM、SIGINT）
#              时自动删除PID文件，确保锁的可靠性。
# 环境:       要求Bash 4.0+，支持trap、kill、readlink等标准工具。
# 许可:       无限制，可自由使用、修改和分发。
#=======================================================================

#========================================================================
# 1. 全局配置
#========================================================================

# 脚本名称（用于日志、错误信息）
SCRIPT_NAME="pid_lock_demo"

# PID文件路径（建议使用绝对路径，避免工作目录影响）
# 若使用/var/run通常需要root权限，此处采用当前目录下的run文件夹
PID_FILE="/tmp/${SCRIPT_NAME}.pid"

# 需要加锁的进程名称标识（用于检查进程是否存活）
# 默认为当前脚本名称，可被覆盖
PROCESS_NAME="${SCRIPT_NAME}"

# 锁目录（可选，用于创建PID文件前检测目录是否存在）
LOCK_DIR="$(dirname "${PID_FILE}")"

# 日志文件（可选，记录启动、退出信息）
LOG_FILE="/tmp/${SCRIPT_NAME}.log"

# 最大等待时间（秒），在清理锁时如果进程残留则等待
MAX_WAIT_SECONDS=10

# 是否启用调试模式（0=关闭，1=开启）
DEBUG=0

#========================================================================
# 2. 日志与错误处理辅助函数
#========================================================================

# 功能: 输出格式化日志（带时间戳）
# 参数: $1 - 日志级别 (INFO, WARN, ERROR, DEBUG)
#        $2 - 日志消息
# 全局变量: LOG_FILE, DEBUG
function log() {
    local level="$1"
    local msg="$2"
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    local log_entry="[${timestamp}] [${level}] ${msg}"

    # 输出到控制台
    echo "${log_entry}" >&2

    # 如果日志文件可写，则追加
    if [[ -w "${LOG_FILE}" ]] || touch "${LOG_FILE}" 2>/dev/null; then
        echo "${log_entry}" >> "${LOG_FILE}"
    fi
}

# 功能: 调试日志 (仅在DEBUG=1时输出)
function debug() {
    if [[ $DEBUG -eq 1 ]]; then
        log "DEBUG" "$@"
    fi
}

# 功能: 错误并退出
# 参数: $1 - 错误消息
#        $2 - 退出码（可选，默认1）
function die() {
    log "ERROR" "$1"
    exit "${2:-1}"
}

#========================================================================
# 3. PID文件锁核心函数
#========================================================================

# 功能: 检查PID文件是否存在且进程存活
# 返回值: 0 - 不需要处理（锁有效，或文件不存在但无进程）
#         1 - 需要退出（锁有效且进程运行）
#         2 - 锁文件失效（进程不存在应被清理）
# 输出: 无
function check_pid_file() {
    if [[ ! -f "${PID_FILE}" ]]; then
        debug "PID文件不存在: ${PID_FILE}"
        return 0
    fi

    # 读取存储的PID
    local stored_pid
    stored_pid=$(cat "${PID_FILE}" 2>/dev/null)
    if [[ -z "${stored_pid}" ]]; then
        log "WARN" "PID文件内容为空，将被视为失效"
        return 2
    fi

    # 检查PID是否为数字
    if ! [[ "${stored_pid}" =~ ^[0-9]+$ ]]; then
        log "WARN" "PID文件内容非数字: ${stored_pid}，将被视为失效"
        return 2
    fi

    # 检查进程是否存在（使用kill -0测试）
    if kill -0 "${stored_pid}" 2>/dev/null; then
        # 进程存在，需要判断是否是我们希望的进程（通过进程名过滤）
        local cmdline
        cmdline=$(cat /proc/"${stored_pid}"/cmdline 2>/dev/null | tr '\0' ' ')
        if [[ "${cmdline}" == *"${PROCESS_NAME}"* ]]; then
            log "ERROR" "进程 ${stored_pid} (${PROCESS_NAME}) 已在运行，PID文件: ${PID_FILE}"
            return 1
        else
            # 进程存在但名称不匹配，可能是其他程序或僵尸，视作失效
            log "WARN" "PID ${stored_pid} 存在但与进程名 '${PROCESS_NAME}' 不匹配，视为旧锁"
            return 2
        fi
    else
        # 进程不存在，锁失效
        log "WARN" "PID ${stored_pid} 对应的进程不存在，PID文件失效"
        return 2
    fi
}

# 功能: 创建PID文件（写锁），原子操作通过重定向实现
# 返回值: 0 成功，非0失败
# 输出: 无
function create_pid_file() {
    local current_pid=$$
    # 确保目录存在
    if ! mkdir -p "${LOCK_DIR}" 2>/dev/null; then
        die "无法创建PID文件目录: ${LOCK_DIR}"
    fi

    # 尝试写入PID文件（O_EXCL效果通过检查文件是否存在来实现）
    # 更可靠的方式：先尝试创建一个临时文件，然后rename到目标
    local tmp_pid_file="${PID_FILE}.$$.tmp"
    echo "${current_pid}" > "${tmp_pid_file}" || {
        rm -f "${tmp_pid_file}"
        die "无法写入临时PID文件: ${tmp_pid_file}"
    }

    # 原子操作：移动临时文件至目标文件
    if ! mv "${tmp_pid_file}" "${PID_FILE}"; then
        rm -f "${tmp_pid_file}"
        die "无法将临时PID文件移至 ${PID_FILE}"
    fi

    log "INFO" "PID文件创建成功: ${PID_FILE} (PID=${current_pid})"
    return 0
}

# 功能: 删除PID文件（清理锁）
# 注意: 仅在当前进程PID与文件内匹配时才删除，避免误删
function remove_pid_file() {
    if [[ ! -f "${PID_FILE}" ]]; then
        return 0
    fi

    local file_pid
    file_pid=$(cat "${PID_FILE}" 2>/dev/null)
    # 如果文件中的PID与当前进程PID相同，则删除
    if [[ "${file_pid}" == "$$" ]]; then
        rm -f "${PID_FILE}"
        log "INFO" "已删除PID文件: ${PID_FILE}"
    else
        # 如果文件内容非数字或为空，直接删除（紧急清理）
        if [[ -z "${file_pid}" ]] || ! [[ "${file_pid}" =~ ^[0-9]+$ ]]; then
            rm -f "${PID_FILE}"
            log "WARN" "强制删除无效PID文件: ${PID_FILE}"
        else
            log "WARN" "跳过清理：PID文件中的PID (${file_pid}) 与当前进程 ($$) 不匹配"
        fi
    fi
}

#========================================================================
# 4. 信号处理与清理函数
#========================================================================

# 功能: 信号处理函数（SIGTERM, SIGINT 等）
# 参数: $1 - 信号名称
# 此函数会在退出前执行清理，并重新发送信号给自己以确保完全终止
function signal_handler() {
    local signal="$1"
    log "INFO" "收到信号 ${signal}，执行清理..."
    remove_pid_file
    log "INFO" "清理完毕，进程退出"
    # 移除自身的信号处理，并重新发送信号来终止（避免无限循环）
    trap - "${signal}"
    kill -"${signal}" $$
}

# 功能: 注册信号处理器
function setup_signal_handlers() {
    local signals
    signals=("SIGTERM" "SIGINT" "SIGHUP" "SIGQUIT" "SIGABRT")
    for sig in "${signals[@]}"; do
        trap "signal_handler ${sig}" "${sig}"
    done
    # 捕获EXIT事件以确保正常退出时也清理
    trap remove_pid_file EXIT
    log "INFO" "信号处理器注册完成"
}

#========================================================================
# 5. 主进程任务（模拟实际工作）
#========================================================================

# 功能: 执行实际业务逻辑（此处为演示循环）
# 生产环境中应替换为真正的进程入口
function run_main_process() {
    log "INFO" "主进程开始运行 (PID=$$)"
    # 模拟长时间运行（60秒后自动退出）
    local counter=0
    while [[ $counter -lt 60 ]]; do
        echo "进程 ${PROCESS_NAME} 正在运行... 第 $((counter+1)) 秒"
        sleep 1
        counter=$((counter+1))
    done
    log "INFO" "主进程完成工作，正常退出"
}

#========================================================================
# 6. 启动入口
#========================================================================

function main() {
    # 显示帮助信息（可选）
    if [[ "$1" == "--help" ]] || [[ "$1" == "-h" ]]; then
        cat <<EOF
用法: $(basename "$0") [选项]
选项:
  --help, -h   显示此帮助信息并退出
  --debug      启用调试模式
  --name NAME  设置进程名称标识（用于锁检查）
  --pidfile PATH 指定PID文件路径
  --logfile PATH 指定日志文件路径
若不指定参数，则使用默认配置。
此脚本实现PID文件锁，防止重复启动。通常作为守护进程启动脚本使用。
EOF
        exit 0
    fi

    # 解析命令行参数（简易版）
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --debug)
                DEBUG=1
                ;;
            --name)
                shift
                PROCESS_NAME="$1"
                ;;
            --pidfile)
                shift
                PID_FILE="$1"
                LOCK_DIR="$(dirname "${PID_FILE}")"
                ;;
            --logfile)
                shift
                LOG_FILE="$1"
                ;;
            *)
                die "未知参数: $1"
                ;;
        esac
        shift
    done

    # 记录启动日志
    log "INFO" "========================================="
    log "INFO" "启动 ${SCRIPT_NAME} 版本 1.0"
    log "INFO" "PID文件: ${PID_FILE}"
    log "INFO" "进程名标识: ${PROCESS_NAME}"
    log "INFO" "日志文件: ${LOG_FILE}"

    # 1. 检查PID文件锁
    check_pid_file
    local check_result=$?
    debug "check_pid_file 返回: ${check_result}"

    case $check_result in
        1)
            # 锁有效，进程已在运行，退出
            log "ERROR" "检测到另一实例正在运行，启动失败"
            exit 1
            ;;
        2)
            # 锁文件失效，清理后继续
            log "WARN" "发现过期的PID文件，尝试清理..."
            remove_pid_file
            # 再次检查是否清理成功（防止并发删除导致残留）
            if [[ -f "${PID_FILE}" ]]; then
                sleep 0.5
                if [[ -f "${PID_FILE}" ]]; then
                    die "无法清理旧的PID文件: ${PID_FILE}"
                fi
            fi
            ;;
        0)
            # 正常情况（无锁）
            ;;
    esac

    # 2. 创建当前进程的PID文件
    create_pid_file || die "创建PID文件失败"

    # 3. 注册信号处理函数
    setup_signal_handlers

    # 4. 执行主进程（阻塞）
    run_main_process

    # 5. 正常退出（EXIT事件会触发remove_pid_file）
    log "INFO" "${SCRIPT_NAME} 正常结束"
    exit 0
}

# 如果直接执行此脚本，则调用main函数
# 如果被source，则不执行main（便于单元测试）
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
```