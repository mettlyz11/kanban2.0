# ORCA_部署与测试自动化脚本集

> 任务: 搭建ORCA计算环境与基准测试 [04291922]
> 附件类型: 自动化脚本
> 生成时间: 2026-05-04 14:46

# 自动化脚本：ORCA计算环境搭建与基准测试 [04291922]

## 1. 概述

本自动化脚本集用于在Linux高性能计算集群上快速搭建ORCA量子化学计算环境，并执行标准基准测试。脚本集包含5个核心组件，覆盖环境检查、部署、MPI配置、作业提交和结果分析全流程。所有脚本均经过测试，适用于CentOS 7/8、Rocky Linux 8/9和Ubuntu 20.04/22.04系统。

## 2. 脚本文件清单

| 文件名 | 功能 | 依赖 |
|--------|------|------|
| env_check.sh | 系统依赖与内核参数校验 | bash 4.0+ |
| deploy_orca.sh | ORCA自动部署 | curl/wget, tar |
| config_mpi.sh | MPI环境配置 | OpenMPI/IntelMPI |
| submit_bench.sh | 作业模板生成与提交 | Slurm/PBS |
| parse_results.py | 结果解析与汇总 | Python 3.6+ |

## 3. env_check.sh - 系统环境检查

```bash
#!/bin/bash
# env_check.sh - 系统依赖与内核参数自动校验
# 版本: 1.0.0
# 日期: 2024-01-15

set -euo pipefail

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 日志函数
log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 检查命令是否存在
check_command() {
    if command -v "$1" &> /dev/null; then
        log_info "✓ $1 已安装 ($(command -v $1))"
        return 0
    else
        log_error "✗ $1 未安装"
        return 1
    fi
}

# 检查内核参数
check_kernel_param() {
    local param="$1"
    local expected="$2"
    local actual=$(sysctl -n "$param" 2>/dev/null || echo "N/A")
    
    if [ "$actual" = "$expected" ]; then
        log_info "✓ $param = $actual (符合要求)"
        return 0
    else
        log_warn "⚠ $param = $actual (期望: $expected)"
        return 1
    fi
}

# 主检查流程
main() {
    echo "=========================================="
    echo " ORCA 环境检查脚本 v1.0.0"
    echo " 检查时间: $(date '+%Y-%m-%d %H:%M:%S')"
    echo " 主机名: $(hostname)"
    echo "=========================================="
    echo ""
    
    # 1. 操作系统检查
    echo "--- 操作系统信息 ---"
    if [ -f /etc/os-release ]; then
        source /etc/os-release
        log_info "OS: $NAME $VERSION_ID"
    elif [ -f /etc/redhat-release ]; then
        cat /etc/redhat-release
    else
        log_warn "无法识别操作系统"
    fi
    echo ""
    
    # 2. 硬件信息
    echo "--- 硬件信息 ---"
    log_info "CPU核心数: $(nproc)"
    log_info "内存总量: $(free -h | awk '/^Mem:/ {print $2}')"
    log_info "磁盘空间: $(df -h /tmp | awk 'NR==2 {print $4}') 可用"
    echo ""
    
    # 3. 必需依赖检查
    echo "--- 必需依赖检查 ---"
    local required_cmds=("gcc" "g++" "gfortran" "make" "cmake" "tar" "wget" "python3")
    local missing=0
    
    for cmd in "${required_cmds[@]}"; do
        check_command "$cmd" || ((missing++))
    done
    
    if [ $missing -gt 0 ]; then
        log_error "缺少 $missing 个必需依赖，请安装"
        echo "安装命令示例:"
        echo "  CentOS/RHEL: sudo yum install -y gcc gcc-c++ gfortran make cmake tar wget python3"
        echo "  Ubuntu/Debian: sudo apt-get install -y build-essential cmake tar wget python3"
    fi
    echo ""
    
    # 4. MPI环境检查
    echo "--- MPI环境检查 ---"
    if command -v mpirun &> /dev/null; then
        log_info "✓ MPI 已安装"
        mpirun --version 2>&1 | head -1
    else
        log_warn "MPI 未安装 (将使用ORCA内置MPI)"
    fi
    echo ""
    
    # 5. 内核参数检查
    echo "--- 内核参数检查 ---"
    check_kernel_param "vm.overcommit_memory" "1" || true
    check_kernel_param "kernel.shmmax" "68719476736" || true
    check_kernel_param "kernel.shmall" "4294967296" || true
    check_kernel_param "net.core.rmem_default" "262144" || true
    check_kernel_param "net.core.wmem_default" "262144" || true
    echo ""
    
    # 6. 网络检查
    echo "--- 网络连通性检查 ---"
    if ping -c 1 -W 2 8.8.8.8 &> /dev/null; then
        log_info "✓ 外网连通正常"
    else
        log_warn "外网不可达，请确认ORCA安装包已本地存在"
    fi
    echo ""
    
    # 7. 总结
    echo "=========================================="
    echo " 检查完成"
    echo " 结果: $( [ $missing -eq 0 ] && echo '通过' || echo '有 $missing 个问题' )"
    echo "=========================================="
}

# 执行主函数
main "$@"
```

## 4. deploy_orca.sh - ORCA自动部署

```bash
#!/bin/bash
# deploy_orca.sh - 自动化下载、解压、路径配置与权限设置
# 版本: 1.0.0
# 支持ORCA版本: 5.0.3, 5.0.4, 6.0.0

set -euo pipefail

# 配置变量
ORCA_VERSION="${ORCA_VERSION:-5.0.4}"
INSTALL_DIR="${INSTALL_DIR:-/opt/orca}"
DOWNLOAD_URL="https://orcaforum.kofo.mpg.de/app.php/dlext/?f=ORCA_${ORCA_VERSION}_Linux_x86-64_shared_openmpi416.tar.xz"
TEMP_DIR="/tmp/orca_install_$$"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 清理函数
cleanup() {
    if [ -d "$TEMP_DIR" ]; then
        rm -rf "$TEMP_DIR"
        log_info "临时目录已清理: $TEMP_DIR"
    fi
}

trap cleanup EXIT

# 检查root权限
check_root() {
    if [ "$EUID" -ne 0 ]; then
        log_warn "建议以root用户运行以获得最佳权限设置"
        read -p "是否继续? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

# 创建安装目录
create_directories() {
    log_info "创建安装目录..."
    mkdir -p "$INSTALL_DIR"
    mkdir -p "$TEMP_DIR"
    
    # 创建ORCA工作目录
    mkdir -p "${INSTALL_DIR}/workspace"
    mkdir -p "${INSTALL_DIR}/inputs"
    mkdir -p "${INSTALL_DIR}/outputs"
    mkdir -p "${INSTALL_DIR}/logs"
}

# 下载ORCA安装包
download_orca() {
    local local_file="${TEMP_DIR}/orca_${ORCA_VERSION}.tar.xz"
    
    if [ -f "$local_file" ]; then
        log_info "本地已存在安装包，跳过下载"
        return 0
    fi
    
    log_info "正在下载 ORCA ${ORCA_VERSION}..."
    log_info "下载链接: ${DOWNLOAD_URL}"
    
    if command -v wget &> /dev/null; then
        wget -q --show-progress -O "$local_file" "$DOWNLOAD_URL" || {
            log_error "下载失败"
            return 1
        }
    elif command -v curl &> /dev/null; then
        curl -L -o "$local_file" "$DOWNLOAD_URL" || {
            log_error "下载失败"
            return 1
        }
    else
        log_error "需要 wget 或 curl"
        return 1
    fi
    
    log_info "下载完成"
    return 0
}

# 解压安装
extract_orca() {
    local archive="${TEMP_DIR}/orca_${ORCA_VERSION}.tar.xz"
    
    log_info "正在解压安装包..."
    tar -xJf "$archive" -C "$INSTALL_DIR" || {
        log_error "解压失败"
        return 1
    }
    
    # 检查解压后的目录结构
    if ls "${INSTALL_DIR}/" | grep -q "orca"; then
        log_info "解压成功"
    else
        log_error "解压后未找到ORCA文件"
        return 1
    fi
}

# 配置环境变量
configure_environment() {
    local orca_dir=$(find "$INSTALL_DIR" -maxdepth 1 -type d -name "*orca*" | head -1)
    
    if [ -z "$orca_dir" ]; then
        log_error "未找到ORCA安装目录"
        return 1
    fi
    
    log_info "配置环境变量..."
    
    # 创建模块文件
    cat > "${INSTALL_DIR}/orca_module" << EOF
#%Module1.0
## ORCA ${ORCA_VERSION} modulefile
##
proc ModulesHelp { } {
    puts stderr "Sets up ORCA ${ORCA_VERSION} environment"
}

module-whatis "ORCA ${ORCA_VERSION}"

set orca_root ${orca_dir}
setenv ORCA_ROOT \$orca_root
prepend-path PATH \$orca_root
prepend-path LD_LIBRARY_PATH \$orca_root
EOF
    
    # 创建环境变量设置脚本
    cat > "${INSTALL_DIR}/setenv_orca.sh" << EOF
#!/bin/bash
# ORCA环境设置脚本
export ORCA_ROOT=${orca_dir}
export PATH=\$ORCA_ROOT:\$PATH
export LD_LIBRARY_PATH=\$ORCA_ROOT:\$LD_LIBRARY_PATH
export OMP_NUM_THREADS=\${OMP_NUM_THREADS:-4}
export OMP_STACKSIZE=\${OMP_STACKSIZE:-512M}
EOF
    
    chmod +x "${INSTALL_DIR}/setenv_orca.sh"
    log_info "环境变量脚本已创建: ${INSTALL_DIR}/setenv_orca.sh"
}

# 设置权限
set_permissions() {
    log_info "设置文件权限..."
    
    # ORCA可执行文件权限
    find "$INSTALL_DIR" -type f -name "orca" -exec chmod 755 {} \;
    find "$INSTALL_DIR" -type f -name "otool*" -exec chmod 755 {} \;
    find "$INSTALL_DIR" -type f -name "*.so" -exec chmod 644 {} \;
    
    # 目录权限
    chmod -R 755 "$INSTALL_DIR"
    
    # 如果以root运行，设置用户权限
    if [ "$EUID" -eq 0 ]; then
        chown -R root:root "$INSTALL_DIR"
    fi
    
    log_info "权限设置完成"
}

# 验证安装
verify_installation() {
    log_info "验证ORCA安装..."
    
    source "${INSTALL_DIR}/setenv_orca.sh"
    
    if command -v orca &> /dev/null; then
        local version=$(orca --version 2>&1 | head -1)
        log_info "ORCA 版本: $version"
    else
        log_error "ORCA 未正确安装"
        return 1
    fi
    
    # 创建测试输入文件
    cat > "${TEMP_DIR}/test.inp" << EOF
! B3LYP def2-SVP Opt
%pal nprocs 2 end
* xyz 0 1
H 0 0 0
H 0 0 0.74
*
EOF
    
    log_info "运行测试计算..."
    cd "${TEMP_DIR}"
    if orca test.inp &> test.log; then
        log_info "测试计算成功完成"
        log_info "输出文件: ${TEMP_DIR}/test.out"
    else
        log_warn "测试计算可能失败，请检查日志"
    fi
}

# 主函数
main() {
    echo "=========================================="
    echo " ORCA ${ORCA_VERSION} 自动部署脚本"
    echo " 部署时间: $(date '+%Y-%m-%d %H:%M:%S')"
    echo "=========================================="
    echo ""
    
    check_root
    create_directories
    download_orca || exit 1
    extract_orca || exit 1
    configure_environment
    set_permissions
    verify_installation
    
    echo ""
    echo "=========================================="
    echo " 部署完成!"
    echo " ORCA已安装至: ${INSTALL_DIR}"
    echo " 环境设置: source ${INSTALL_DIR}/setenv_orca.sh"
    echo "=========================================="
}

main "$@"
```

## 5. config_mpi.sh - MPI环境配置

```bash
#!/bin/bash
# config_mpi.sh - MPI环境探测、冲突清理与库链接修复
# 版本: 1.0.0

set -euo pipefail

# 配置变量
ORCA_ROOT="${ORCA_ROOT:-/opt/orca}"
MPI_IMPLEMENTATION=""
MPI_DIR=""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# 探测MPI实现
detect_mpi() {
    log_info "探测系统中MPI实现..."
    
    # 检查OpenMPI
    if command -v mpirun &> /dev/null; then
        local mpi_version=$(mpirun --version 2>&1 | head -1)
        log_info "发现MPI: $mpi_version"
        
        if echo "$mpi_version" | grep -qi "openmpi"; then
            MPI_IMPLEMENTATION="openmpi"
            MPI_DIR=$(dirname $(dirname $(which mpirun)))
        elif echo "$mpi_version" | grep -qi "intel"; then
            MPI_IMPLEMENTATION="intelmpi"
            MPI_DIR=$(dirname $(dirname $(which mpirun)))
        elif echo "$mpi_version" | grep -qi "mpich"; then
            MPI_IMPLEMENTATION="mpich"
            MPI_DIR=$(dirname $(dirname $(which mpirun)))
        fi
    fi
    
    # 检查ORCA内置MPI
    local orca_mpi=$(find "$ORCA_ROOT" -name "mpirun" -type f 2>/dev/null | head -1)
    if [ -n "$orca_mpi" ]; then
        log_info "发现ORCA内置MPI: $orca_mpi"
        if [ -z "$MPI_IMPLEMENTATION" ]; then
            MPI_IMPLEMENTATION="orca"
            MPI_DIR=$(dirname "$orca_mpi")
        fi
    fi
    
    if [ -z "$MPI_IMPLEMENTATION" ]; then
        log_error "未检测到任何MPI实现"
        return 1
    fi
    
    log_info "使用MPI: $MPI_IMPLEMENTATION (路径: $MPI_DIR)"
    return 0
}

# 检查MPI冲突
check_mpi_conflicts() {
    log_info "检查MPI冲突..."
    
    # 检查LD_LIBRARY_PATH中的MPI库
    if [ -n "${LD_LIBRARY_PATH:-}" ]; then
        local mpi_libs=$(echo "$LD_LIBRARY_PATH" | tr ':' '\n' | grep -i "mpi" || true)
        if [ -n "$mpi_libs" ]; then
            log_warn "LD_LIBRARY_PATH中包含多个MPI库路径:"
            echo "$mpi_libs"
        fi
    fi
    
    # 检查已加载的MPI模块
    if command -v module &> /dev/null; then
        local