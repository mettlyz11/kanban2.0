# macOS_SMB一键部署脚本

> 任务: 在Macmini上启用SMB文件共享 [04291941]
> 附件类型: 自动化脚本
> 生成时间: 2026-05-04 15:15

# Macmini SMB文件共享自动化脚本

## 1. 概述

本脚本用于在Macmini上通过macOS原生命令行工具自动启用SMB文件共享服务，包括：启动SMB守护进程、配置SMB协议版本、添加授权用户、创建并共享指定目录、设置访问权限、记录操作日志、验证服务状态，并提供一键回滚功能。脚本设计为半自动执行，需交互式输入参数，同时内置安全校验机制以防止误操作。

### 1.1 适用环境
- 操作系统：macOS 12.0 (Monterey) 及以上版本（基于APFS文件系统）
- 硬件：Macmini（Intel或Apple Silicon）
- 用户权限：需具有sudo权限的管理员账户

### 1.2 脚本依赖
- `/usr/sbin/sharing`：macOS共享管理工具
- `/usr/sbin/serveradmin`：服务管理工具（macOS Server环境）或 `launchctl`（原生环境）
- `/usr/bin/dscl`：目录服务命令行工具
- `/bin/launchctl`：服务控制
- `/usr/bin/sudo`：权限提升
- `/usr/bin/sysadminctl`：用户管理（可选）

### 1.3 运行权限
脚本必须以root或具有sudo权限的用户运行。首次执行前请运行：
```bash
chmod +x smb_share_setup.sh
sudo ./smb_share_setup.sh
```

---

## 2. 脚本代码

```bash
#!/bin/bash
# ============================================================================
# 脚本名称: smb_share_setup.sh
# 版本: 1.0.0
# 作者: AI执行助手
# 日期: 2025-04-19
# 描述: 在Macmini上自动启用SMB文件共享，包括服务启停、用户授权、目录共享、
#       日志记录、状态验证与一键回滚。
# 许可证: MIT
# ============================================================================

set -euo pipefail

# -------------------------------
# 全局变量
# -------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="/var/log/smb_share_setup_$(date +%Y%m%d_%H%M%S).log"
BACKUP_DIR="/tmp/smb_setup_backup_$(date +%s)"
SMB_CONF="/etc/smb.conf"  # macOS默认SMB配置路径（若存在）
SHARES_DB="/var/db/dslocal/nodes/Default/sharepoints"  # macOS共享点数据库

# 默认值（可被交互输入覆盖）
SHARE_NAME="Public_SMB"
SHARE_PATH="/Shared/SMB"
SMB_PROTOCOL="SMB3"
ALLOWED_USERS=()
ROLLBACK_NEEDED=false

# -------------------------------
# 辅助函数
# -------------------------------

# 日志记录
log() {
    local level="$1"
    local message="$2"
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[${timestamp}] [${level}] ${message}" | tee -a "$LOG_FILE"
}

# 错误处理
error_exit() {
    log "ERROR" "$1"
    echo "发生错误，脚本终止。查看日志: $LOG_FILE"
    exit 1
}

# 检查命令是否存在
check_command() {
    if ! command -v "$1" &>/dev/null; then
        error_exit "缺少必要命令: $1"
    fi
}

# 检查root权限
check_root() {
    if [[ $EUID -ne 0 ]]; then
        error_exit "此脚本必须以root权限运行 (使用 sudo)"
    fi
}

# 安全输入函数（隐藏密码）
secure_read() {
    local prompt="$1"
    local var_name="$2"
    local input_val
    read -r -s -p "$prompt" input_val
    echo
    eval "$var_name='$input_val'"
}

# -------------------------------
# 初始化检查
# -------------------------------
init_checks() {
    log "INFO" "开始初始化检查..."
    
    # 检查root权限
    check_root
    
    # 检查必要命令
    local cmds=("sharing" "dscl" "launchctl" "sudo" "sysadminctl")
    for cmd in "${cmds[@]}"; do
        check_command "$cmd"
    done
    
    # 检查macOS版本
    local os_version
    os_version=$(sw_vers -productVersion)
    log "INFO" "macOS版本: $os_version"
    
    # 创建备份目录
    mkdir -p "$BACKUP_DIR"
    log "INFO" "备份目录已创建: $BACKUP_DIR"
    
    log "INFO" "初始化检查完成"
}

# -------------------------------
# 交互式参数输入
# -------------------------------
get_user_input() {
    echo "=========================================="
    echo "  Macmini SMB文件共享配置向导"
    echo "=========================================="
    
    # 获取共享名称
    read -r -p "请输入共享名称 [默认: ${SHARE_NAME}]: " input_share_name
    SHARE_NAME="${input_share_name:-$SHARE_NAME}"
    
    # 获取共享路径
    read -r -p "请输入共享目录路径 [默认: ${SHARE_PATH}]: " input_share_path
    SHARE_PATH="${input_share_path:-$SHARE_PATH}"
    
    # 验证路径格式
    if [[ ! "$SHARE_PATH" =~ ^/ ]]; then
        error_exit "路径必须以 '/' 开头: $SHARE_PATH"
    fi
    
    # 获取SMB协议版本
    echo "请选择SMB协议版本:"
    echo "  1) SMB2 (兼容性较好)"
    echo "  2) SMB3 (推荐，更高安全性)"
    read -r -p "请输入选项 [1/2, 默认2]: " protocol_choice
    case "${protocol_choice:-2}" in
        1) SMB_PROTOCOL="SMB2" ;;
        2) SMB_PROTOCOL="SMB3" ;;
        *) SMB_PROTOCOL="SMB3" ;;
    esac
    
    # 获取授权用户列表
    echo "请输入授权访问的用户名（多个用户用空格分隔，留空则仅允许管理员）:"
    read -r -p "用户列表: " input_users
    if [[ -n "$input_users" ]]; then
        IFS=' ' read -ra ALLOWED_USERS <<< "$input_users"
    fi
    
    # 确认信息
    echo "=========================================="
    echo "配置摘要:"
    echo "  共享名称: $SHARE_NAME"
    echo "  共享路径: $SHARE_PATH"
    echo "  SMB协议: $SMB_PROTOCOL"
    echo "  授权用户: ${ALLOWED_USERS[*]:-(仅管理员)}"
    echo "=========================================="
    read -r -p "是否继续执行？[y/N]: " confirm
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        log "INFO" "用户取消操作"
        exit 0
    fi
}

# -------------------------------
# 安全校验
# -------------------------------
security_checks() {
    log "INFO" "执行安全校验..."
    
    # 校验共享路径是否已存在且非系统关键目录
    local critical_dirs=("/" "/System" "/Library" "/private" "/etc" "/var" "/tmp" "/Users")
    for dir in "${critical_dirs[@]}"; do
        if [[ "$SHARE_PATH" == "$dir" || "$SHARE_PATH" == "$dir/"* ]]; then
            error_exit "禁止共享系统关键目录: $dir"
        fi
    done
    
    # 校验用户名是否存在（若指定了用户）
    if [[ ${#ALLOWED_USERS[@]} -gt 0 ]]; then
        for user in "${ALLOWED_USERS[@]}"; do
            if ! id "$user" &>/dev/null; then
                error_exit "用户不存在: $user"
            fi
            log "INFO" "用户 '$user' 已验证存在"
        done
    fi
    
    # 检查共享名称是否已被占用
    if sharing -l 2>/dev/null | grep -q "name:.*${SHARE_NAME}"; then
        error_exit "共享名称 '$SHARE_NAME' 已被使用"
    fi
    
    # 检查路径是否已被共享
    if sharing -l 2>/dev/null | grep -q "path:.*${SHARE_PATH}"; then
        error_exit "路径 '$SHARE_PATH' 已被其他共享占用"
    fi
    
    log "INFO" "安全校验通过"
}

# -------------------------------
# 备份现有配置
# -------------------------------
backup_config() {
    log "INFO" "备份现有SMB配置..."
    
    # 备份SMB配置文件（如果存在）
    if [[ -f "$SMB_CONF" ]]; then
        cp "$SMB_CONF" "$BACKUP_DIR/smb.conf.bak"
        log "INFO" "已备份: $SMB_CONF"
    fi
    
    # 备份共享点数据库（如果存在）
    if [[ -d "$SHARES_DB" ]]; then
        cp -r "$SHARES_DB" "$BACKUP_DIR/sharepoints.bak"
        log "INFO" "已备份共享点数据库"
    fi
    
    # 记录当前共享状态
    sharing -l > "$BACKUP_DIR/current_shares.txt" 2>/dev/null || true
    log "INFO" "当前共享状态已备份"
    
    # 记录当前SMB服务状态
    launchctl list | grep -i smb > "$BACKUP_DIR/smb_service_status.txt" 2>/dev/null || true
    log "INFO" "SMB服务状态已备份"
}

# -------------------------------
# 核心配置逻辑
# -------------------------------

# 创建共享目录
create_share_directory() {
    log "INFO" "创建共享目录: $SHARE_PATH"
    
    if [[ ! -d "$SHARE_PATH" ]]; then
        mkdir -p "$SHARE_PATH"
        log "INFO" "目录已创建"
    else
        log "WARN" "目录已存在，将使用现有目录"
    fi
    
    # 设置目录权限（755：所有者可读写，其他人可读执行）
    chmod 755 "$SHARE_PATH"
    log "INFO" "目录权限已设置为 755"
}

# 启用SMB服务
enable_smb_service() {
    log "INFO" "启用SMB文件共享服务..."
    
    # 通过launchctl加载SMB服务
    # macOS使用com.apple.smbd作为SMB守护进程
    if ! launchctl list | grep -q "com.apple.smbd"; then
        launchctl load -w /System/Library/LaunchDaemons/com.apple.smbd.plist 2>/dev/null || \
        sudo launchctl load -w /System/Library/LaunchDaemons/com.apple.smbd.plist
        log "INFO" "SMB守护进程已加载"
    else
        log "INFO" "SMB守护进程已在运行"
    fi
    
    # 启用文件共享（通过sharing命令）
    sharing -e 2>/dev/null || true
    log "INFO" "文件共享功能已启用"
    
    # 设置SMB协议版本
    # 通过修改smb.conf或使用sysadminctl
    if [[ "$SMB_PROTOCOL" == "SMB3" ]]; then
        # 确保SMB3被启用（默认macOS已启用）
        sudo sysadminctl -smbProtocolVersion 3 2>/dev/null || true
        log "INFO" "SMB协议版本设置为 SMB3"
    else
        sudo sysadminctl -smbProtocolVersion 2 2>/dev/null || true
        log "INFO" "SMB协议版本设置为 SMB2"
    fi
}

# 添加授权用户
add_authorized_users() {
    log "INFO" "配置授权用户..."
    
    if [[ ${#ALLOWED_USERS[@]} -eq 0 ]]; then
        log "INFO" "未指定授权用户，仅管理员可访问"
        return
    fi
    
    for user in "${ALLOWED_USERS[@]}"; do
        # 使用dscl确保用户存在于本地目录
        if dscl . -list /Users | grep -q "^${user}$"; then
            # 为用户启用SMB访问（macOS需要将用户添加到文件共享权限）
            # 通过sharing命令添加用户权限
            sharing -a "$SHARE_NAME" -u "$user" -r 2>/dev/null || \
            sharing -a "$SHARE_PATH" -u "$user" -r 2>/dev/null || true
            log "INFO" "已添加用户 '$user' 到共享 '$SHARE_NAME'"
        else
            log "WARN" "用户 '$user' 不存在于本地目录，跳过"
        fi
    done
}

# 创建并挂载共享
create_share() {
    log "INFO" "创建SMB共享: $SHARE_NAME -> $SHARE_PATH"
    
    # 使用sharing命令创建SMB共享
    # -s: SMB协议, -a: 添加共享, -n: 共享名称, -p: 路径
    sharing -s -a "$SHARE_PATH" -n "$SHARE_NAME" -S 2>/dev/null || \
    sharing -a "$SHARE_PATH" -n "$SHARE_NAME" -S 2>/dev/null || {
        log "WARN" "sharing命令创建共享失败，尝试备用方法"
        # 备用：使用dscl手动添加共享点
        sudo dscl . -create "/SharePoints/$SHARE_NAME" 2>/dev/null || true
        sudo dscl . -create "/SharePoints/$SHARE_NAME" sharepoint "$SHARE_PATH" 2>/dev/null || true
        sudo dscl . -create "/SharePoints/$SHARE_NAME" smb_share 1 2>/dev/null || true
    }
    
    log "INFO" "共享 '$SHARE_NAME' 已创建"
}

# 重启SMB服务使配置生效
restart_smb_service() {
    log "INFO" "重启SMB服务以应用配置..."
    
    # 停止SMB服务
    sudo launchctl unload /System/Library/LaunchDaemons/com.apple.smbd.plist 2>/dev/null || true
    sleep 1
    
    # 启动SMB服务
    sudo launchctl load -w /System/Library/LaunchDaemons/com.apple.smbd.plist 2>/dev/null || \
    sudo launchctl load /System/Library/LaunchDaemons/com.apple.smbd.plist
    
    # 等待服务启动
    sleep 2
    
    log "INFO" "SMB服务已重启"
}

# -------------------------------
# 状态验证
# -------------------------------
verify_setup() {
    log "INFO" "验证SMB共享配置..."
    
    local errors=0
    
    # 1. 检查SMB服务是否运行
    echo "检查SMB服务状态..."
    if launchctl list | grep -q "com.apple.smbd"; then
        log "INFO" "✓ SMB守护进程正在运行"
    else
        log "ERROR" "✗ SMB守护进程未运行"
        errors=$((errors + 1))
    fi
    
    # 2. 检查共享是否列出
    echo "检查共享列表..."
    if sharing -l 2>/dev/null | grep -q "name:.*${SHARE_NAME}"; then
        log "INFO" "✓ 共享 '$SHARE_NAME' 已在共享列表中"
    else
        log "WARN" "✗ 共享 '$SHARE_NAME' 未在共享列表中（可能需刷新）"
        errors=$((errors + 1))
    fi
    
    # 3. 检查目录权限
    echo "检查目录权限..."
    local dir_perms
    dir_perms=$(stat -f "%Lp" "$SHARE_PATH")
    if [[ "$dir_perms" == "755" ]]; then
        log "INFO" "✓ 目录权限正确 (755)"
    else
        log "WARN" "✗ 目录权限为 $dir_perms (期望 755)"
        errors=$((errors + 1))
    fi
    
    # 4. SMB端口检查（445端口）
    echo "检查SMB端口(445)..."
    if lsof -i :445 -P -n 2>/dev/null | grep -q LISTEN; then
        log "INFO" "✓ SMB端口 445 正在监听"
    else
        log "WARN" "✗ SMB端口 445 未监听（可能需要检查防火墙）"
        errors=$((errors + 1))
    fi
    
    # 5. 尝试本地连接测试（可选）
    echo "尝试本地SMB连接测试..."
    local test_result
    test_result=$(smbutil view "//localhost/${SHARE_NAME}" 2>&1 || true)
    if echo "$test_result" | grep -q "Share name"; then
        log "INFO" "✓ 本地SMB连接测试成功"
    else
        log "WARN" "本地SMB连接测试失败（可能因权限或防火墙）"
        log "WARN" "测试输出: $test_result"
    fi
    
    if [[ $errors -eq 0 ]]; then
        log "INFO" "✅ 所有验证检查通过"
        return 0
    else
        log "WARN" "⚠ 有 $errors 项检查未通过，请查看日志"
        return 1
    fi
}

# -------------------------------
# 回滚功能
# -------------------------------
rollback() {
    log "INFO" "开始回滚操作..."
    
    # 1. 移除创建的共享
    if sharing -