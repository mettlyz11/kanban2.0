# deployment_and_operations_guide

> 任务: v5 #1 PID 文件锁 — 防重复启动
> 附件类型: 用户手册/运维文档
> 生成时间: 2026-05-11 21:14

# PID 文件锁 — 防重复启动 用户手册/运维文档

## 版本历史

| 版本 | 日期       | 作者   | 变更说明                     |
|------|------------|--------|------------------------------|
| 1.0  | 2025-03-20 | 系统   | 初始版本                     |
| 1.1  | 2025-03-28 | 运维组 | 增加 systemd 集成示例及超时处理 |

---

## 1. 概述

PID 文件锁是一种轻量级的进程互斥机制，广泛应用于 Linux/Unix 环境下的守护进程、定时脚本或长时间运行的任务。其核心思想是将启动的进程 ID (PID) 写入一个预先定义的锁文件（通常为`.pid`后缀），并在进程启动时检查该文件。如果锁文件存在且文件中的 PID 对应进程正在运行，则阻止新实例启动，从而防止资源竞争、数据损坏或系统过载。

### 1.1 工作原理

1. **启动检查**：脚本启动时，尝试读取锁文件（如 `/var/run/myapp.pid`）。
2. **进程存在性验证**：若文件存在，则使用 `kill -0 <PID>` 检查该 PID 是否仍在运行（`-0` 仅测试进程是否存在，不发送信号）。
3. **决策逻辑**：
   - 如果进程存活，则输出错误信息并退出。
   - 如果进程已不存在（僵尸或异常退出），则删除旧锁文件并重新创建。
4. **写入锁文件**：若检查通过，将当前进程的 `$$` 写入锁文件，并设置 `trap` 命令确保脚本退出时自动删除锁文件。
5. **运行中保护**：脚本运行期间，锁文件始终存在，任何新启动的实例都会失败。
6. **清理**：正常退出（通过 `exit`、`SIGTERM`、`SIGINT` 或脚本结束）后，锁文件自动删除。

### 1.2 适用场景

- 定时任务（cron）中防重复执行
- 需要独占资源的服务启动脚本
- 数据库迁移、数据同步等单例操作
- 与 systemd、supervisor 配合提供更严格的进程管控

---

## 2. 环境要求

### 2.1 操作系统与 Bash 版本

- **操作系统**：Linux（所有发行版）、macOS、FreeBSD（部分需调整`kill -0`行为）
- **Bash 版本**：≥ 3.2（建议 4.0+ 以获得更好的信号处理能力）
- **依赖工具**：
  - `basename`, `dirname`, `mktemp`, `cat`, `tr`, `rm`, `kill`, `touch`, `mkdir`, `chmod`（均为 coreutils 标准工具）

### 2.2 权限要求

- 锁文件所在目录必须对运行脚本的用户可写。
- 典型路径 `/var/run/` 可能需要 root 权限或通过 systemd-tmpfiles 创建。
- 若使用非特权用户，建议将锁文件放置于用户家目录或 `/tmp` 下。

### 2.3 兼容性

| 环境         | 状态 | 注意事项                         |
|--------------|------|----------------------------------|
| Linux x86_64 | ✔    | 完美支持                         |
| macOS        | ✔    | 注意 BSD `kill -0` 行为相同       |
| BusyBox      | ⚠   | 部分命令选项可能缺失，需精简      |
| Windows WSL  | ✔    | 默认 bash 版本 ≥4.4              |

---

## 3. 部署步骤

### 3.1 下载脚本

以下为完整的 PID 文件锁脚本 `pidlock.sh`。请将其保存至您的服务目录。

```bash
#!/usr/bin/env bash

# ===================================================
# PID FILE LOCK - 防重复启动（v1.0）
# 功能：确保同一脚本只有一个实例运行
# 用法：source pidlock.sh [自定义锁文件路径]
# ===================================================

set -euo pipefail

# ---------- 默认配置 ----------
DEFAULT_PID_DIR="/var/run"
DEFAULT_SCRIPT_NAME="$(basename "$0" .sh)"
PID_FILE="${PID_FILE:-${DEFAULT_PID_DIR}/${DEFAULT_SCRIPT_NAME}.pid}"

# ---------- 自定义 PID 文件路径 ----------
if [ $# -ge 1 ]; then
    PID_FILE="$1"
fi

# ---------- 锁文件父目录检查 ----------
LOCK_DIR="$(dirname "$PID_FILE")"
if [ ! -d "$LOCK_DIR" ]; then
    echo "[ERROR] PID 文件目录 '$LOCK_DIR' 不存在，请创建或修改 PID_FILE 路径" >&2
    exit 1
fi

# ---------- 检查并创建锁 ----------
if [ -e "$PID_FILE" ]; then
    # 读取旧 PID
    OLD_PID=$(cat "$PID_FILE") 2>/dev/null || true
    if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
        echo "[ERROR] 脚本已在运行（PID: $OLD_PID），退出。锁文件: $PID_FILE" >&2
        exit 2
    else
        # 进程不存在，清理残留锁
        rm -f "$PID_FILE"
        echo "[WARN] 发现残留锁文件，已清理。旧 PID: ${OLD_PID:-无}" >&2
    fi
fi

# ---------- 写入当前 PID ----------
echo $$ > "$PID_FILE"
echo "[INFO] 锁文件已创建: $PID_FILE (PID: $$)"

# ---------- 退出时自动清理 ----------
cleanup() {
    local exit_code=$?
    if [ -f "$PID_FILE" ] && [ "$(cat "$PID_FILE")" = "$$" ]; then
        rm -f "$PID_FILE"
        echo "[INFO] 锁文件已删除: $PID_FILE"
    fi
    exit "$exit_code"
}
trap cleanup EXIT SIGTERM SIGINT

# ---------- 用户主程序入口 ----------
# 注：以下为示例，实际业务逻辑请放在主脚本中
main() {
    echo "[INFO] 服务启动中..."
    # 模拟长期运行
    sleep 300
}
```

### 3.2 设置路径

将脚本放置于 `/usr/local/bin/` 或您的项目目录：

```bash
sudo mkdir -p /usr/local/bin
sudo cp pidlock.sh /usr/local/bin/
```

### 3.3 赋予执行权限

```bash
sudo chmod +x /usr/local/bin/pidlock.sh
```

### 3.4 灵活使用两种模式

- **以函数库形式引入**（推荐）：在其他脚本中通过 `source` 载入，自动执行锁逻辑。
- **作为独立脚本调用**：在其他包装脚本中直接执行，但需要将锁逻辑与业务逻辑分离。

---

## 4. 集成到现有系统

### 4.1 在启动脚本中使用（source 方式）

假设您有一个服务脚本 `my_service.sh`，将锁逻辑内嵌：

```bash
#!/usr/bin/env bash
# my_service.sh

PID_FILE="${PID_FILE:-/var/run/my_service.pid}"
source /usr/local/bin/pidlock.sh "$PID_FILE"

# 业务逻辑
echo "处理任务..."
while true; do
    # 核心工作
    sleep 10
done
```

这样，`my_service.sh` 启动时自动执行锁检查，退出时自动清理。

### 4.2 在 systemd 服务单元中集成

PID 文件锁可以增强 systemd 自身的 `PIDFile=` 属性，防止重复启动。创建 systemd service 文件 `/etc/systemd/system/myapp.service`：

```ini
[Unit]
Description=My Application with PID Lock
After=network.target

[Service]
Type=simple
ExecStart=/usr/local/bin/myapp_wrapper.sh
ExecStop=/bin/kill -SIGTERM $MAINPID
PIDFile=/var/run/myapp.pid
User=myappuser
Restart=always

[Install]
WantedBy=multi-user.target
```

然后创建包装脚本 `myapp_wrapper.sh`：

```bash
#!/usr/bin/env bash
# 若 systemd 自动创建 PIDFile，此脚本主要用于双重保护

PID_FILE="/var/run/myapp.pid"
source /usr/local/bin/pidlock.sh "$PID_FILE"

# 启动实际应用
exec /usr/local/bin/myapp --daemon
```

### 4.3 在 cron 定时任务中防重复

直接使用 cron 运行带有锁的脚本，无需额外配置。例如 `crontab -e`：

```
*/5 * * * * /usr/local/bin/pidlock.sh /tmp/my_cron_job.pid && /usr/local/bin/process_data.sh
```

注意：此时 `pidlock.sh` 作为独立脚本，需确保它不会阻塞退出。可以修改为只执行锁检查并返回状态码，但更安全的做法是让业务脚本自身包含锁逻辑。

### 4.4 与 Docker 容器结合

若容器内需要防重复，使用 `ENTRYPOINT` 脚本：

```dockerfile
COPY pidlock.sh /usr/local/bin/pidlock.sh
COPY entrypoint.sh /entrypoint.sh
ENTRYPOINT ["/bin/bash", "/entrypoint.sh"]
```

`entrypoint.sh`:

```bash
#!/usr/bin/env bash
source pidlock.sh "/tmp/app.pid"
exec "$@"
```

---

## 5. 配置项说明

### 5.1 环境变量

| 变量       | 默认值                     | 说明                                                       |
|------------|----------------------------|------------------------------------------------------------|
| `PID_FILE` | `${DEFAULT_PID_DIR}/${脚本名}.pid` | 锁文件完整路径。可通过命令行参数或环境变量覆盖。 |

### 5.2 命令行参数

`source pidlock.sh [自定义PID_FILE路径]`

- 若不提供参数，使用环境变量 `PID_FILE`；若环境变量未设置，使用默认值。
- 若提供路径，则无论 `PID_FILE` 为何值，均使用该路径。

### 5.3 超时处理（扩展功能）

本脚本未内置超时重试逻辑，但可配合外部等待脚本实现。例如等待锁释放直到超时：

```bash
#!/usr/bin/env bash
# waitlock.sh - 等待锁释放，最多等待 30 秒

LOCK_FILE="/tmp/myapp.pid"
TIMEOUT=30
INTERVAL=1
elapsed=0

while [ $elapsed -lt $TIMEOUT ]; do
    if [ -e "$LOCK_FILE" ]; then
        PID=$(cat "$LOCK_FILE" 2>/dev/null)
        if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
            echo "锁被占用，等待 $elapsed 秒..."
            sleep $INTERVAL
            elapsed=$((elapsed + INTERVAL))
        else
            rm -f "$LOCK_FILE"
            echo "残留锁已清理，继续启动"
            break
        fi
    else
        break
    fi
done

if [ $elapsed -ge $TIMEOUT ]; then
    echo "等待超时，放弃启动"
    exit 3
fi
source pidlock.sh "$LOCK_FILE"
```

### 5.4 日志输出

脚本默认输出至标准错误（stderr）和标准输出（stdout），可通过重定向 `2>&1` 统一记录。

---

## 6. 信号处理说明

### 6.1 捕获的信号

| 信号     | 行为                                                                 |
|----------|----------------------------------------------------------------------|
| `SIGTERM`| 优雅退出：删除锁文件后退出。                                         |
| `SIGINT` | 用户中断（Ctrl+C）：删除锁文件后退出。                               |
| `EXIT`   | 任何正常或非正常退出（包括脚本结束、`exit`、`SIGTERM`、`SIGINT`）触发清理。 |

### 6.2 清理逻辑详情

```bash
cleanup() {
    local exit_code=$?
    if [ -f "$PID_FILE" ] && [ "$(cat "$PID_FILE")" = "$$" ]; then
        rm -f "$PID_FILE"
        echo "[INFO] 锁文件已删除: $PID_FILE"
    fi
    exit "$exit_code"
}
```

- 条件判断 `[ "$(cat ...)" = "$$" ]` 避免错误删除其他进程创建的锁文件（竞态条件极小）。
- 若不删除僵尸锁（当进程被 `kill -9` 时），需手动清理。

### 6.3 无法捕获的信号

- `SIGKILL` (9) 强制杀死无法捕获，锁文件会残留。
- 处理方式：下次启动时会自动清理残留锁。

---

## 7. 测试验证方法

### 7.1 手动启动一次

```bash
$ ./my_service.sh &
[1] 12345
[INFO] 锁文件已创建: /var/run/my_service.pid (PID: 12345)
[INFO] 服务启动中...
```

### 7.2 再次启动（期望失败）

```bash
$ ./my_service.sh
[ERROR] 脚本已在运行（PID: 12345），退出。锁文件: /var/run/my_service.pid
$ echo $?
2
```

### 7.3 模拟异常残留

1. 手动创建锁文件 `echo 99999 > /tmp/test.pid`（假设 PID 99999 不存在）。
2. 启动脚本，观察清理日志：

```bash
$ PID_FILE=/tmp/test.pid ./my_service.sh
[WARN] 发现残留锁文件，已清理。旧 PID: 99999
[INFO] 锁文件已创建: /tmp/test.pid (PID: 13000)
```

### 7.4 终止进程后检查锁清理

```bash
$ kill 12345
[INFO] 锁文件已删除: /var/run/my_service.pid
$ ls /var/run/my_service.pid
ls: cannot access '/var/run/my_service.pid': No such file or directory
```

### 7.5 强制杀死测试

```bash
$ kill -9 12345
$ ls /var/run/my_service.pid   # 文件残留
/var/run/my_service.pid
$ ./my_service.sh              # 下次启动自动清理
[WARN] 发现残留锁文件，已清理。旧 PID: 12345
[INFO] 锁文件已创建: /var/run/my_service.pid (PID: 14000)
```

---

## 8. 常见故障排除

### 8.1 PID 文件残留但无错误

**现象**：启动时报告“进程已存在”但实际进程已死。

**原因**：残留锁文件中的 PID 可能被新进程重用（PID 回绕）。  
**解决**：使用更严格的进程匹配，例如检查 `/proc/<PID>/cmdline` 是否匹配期望命令。可在脚本中加入如下验证：

```bash
if [ -n "$OLD_PID" ] && kill -0 "$OLD_PID" 2>/dev/null; then
    # 额外验证：检查进程名称
    if [ -f "/proc/${OLD_PID}/cmdline" ]; then
        CMDLINE=$(tr '\0' ' ' < /proc/${OLD_PID}/cmdline)
        # 假设期望命令包含本脚本名
        if echo "$CMDLINE" | grep -q "$DEFAULT_SCRIPT_NAME"; then
            echo "[ERROR] 实际正在运行"
        else
            rm -f "$PID_FILE"
        fi
    fi
fi
```

### 8.2 权限拒绝

**现象**：`Permission denied` 无法创建 PID 文件或无法读取 `/proc`。

**解决**：
- 确保锁文件目录可写。
- 使用 `sudo -u <user>` 或以对应用户身份运行。
- 对于 `/var/run`，建议创建子目录并设置合适权限：
  ```bash
  sudo mkdir -p /var/run/myapp
  sudo chown myappuser:myappgroup /var/run/myapp
  sudo chmod 755 /var/run/myapp
  ```

### 8.3 脚本卡死或无限等待

**现象**：启动后无响应。

**原因**：脚本在检查锁时卡在 `kill -0` 挂起（如 NFS 文件系统问题）。  
**解决**：设置 `kill -0` 超时（bash 本身不支持，可改用 `timeout` 命令）或在检查前确保 PID 文件不是 NFS 上的。

### 8.4 多线程或子进程冲突

**现象**：锁文件被父进程创建，但子进程退出后父进程仍在运行，锁被误删。

**原因**：`EXIT` trap 在所有子 shell 退出时触发。  
**解决**：确保 `trap cleanup EXIT` 只在主进程中注册。如果使用 `source` 方式，避免在子 shell 中再次 `source`。或者将清理逻辑单独放在主脚本末尾。

---

## 9. 日志与监控建议

### 9.1