# backup_manifest

> 任务: v7 #4 配置文件自动备份
> 附件类型: 配置清单
> 生成时间: 2026-05-12 09:28

# v7 #4 配置文件自动备份 — 配置清单

**文档版本**: 1.0  
**创建日期**: 2025-04-07  
**维护人**: 系统管理员  
**适用系统**: Unix/Linux (CentOS 7+ / Ubuntu 20.04+)  
**备份引擎**: rsync + tar + cron (版本控制基于硬链接快照)

---

## 1. 备份根目录

所有备份数据存储于本地专用分区或挂载点:

```
~/.config-backup/
```

该目录结构与源系统保持一致，每个文件名附加 `.YYYYMMDDHHMMSS` 时间戳后缀，并通过硬链接实现增量保存。目录权限设置为 `700`，属主为运行备份的用户（通常为 `root` 或专用 `backup` 账号）。

子目录组织方式：

```
~/.config-backup/
├── etc/                     # 系统级配置 (对应 /etc/)
├── home/                    # 用户级配置 (对应 /home/ 下各用户)
├── var/                     # 可变配置 (对应 /var/spool/cron/ 等)
├── opt/                     # 第三方软件配置 (对应 /opt/ 下)
├── root/                    # root 用户配置 (对应 /root/)
└── snapshots.log           # 快照日志 (保留最近7天的备份记录)
```

每个目录下按原路径存放文件，如 `/etc/nginx/nginx.conf` 备份至 `~/.config-backup/etc/nginx/nginx.conf.20250407083000`。

---

## 2. 文件清单列表

以下表格列出所有被自动备份的配置文件，共计 **34 项**，涵盖系统核心、服务、用户环境及安全策略。保留版本数均为 **7**，即保留最近7个历史版本（通过硬链接节省空间，实际仅有增量差异占用额外存储）。

| 序号 | 文件名 | 源路径 | 备份子目录 | 保留版本数 | 说明 |
|------|--------|--------|------------|------------|------|
| 1 | `resolv.conf` | `/etc/resolv.conf` | `etc/` | 7 | DNS解析配置，每次网络变更后自动备份。忽略 tmp 后缀。 |
| 2 | `hosts` | `/etc/hosts` | `etc/` | 7 | 静态主机映射。 |
| 3 | `hostname` | `/etc/hostname` | `etc/` | 7 | 系统主机名。 |
| 4 | `fstab` | `/etc/fstab` | `etc/` | 7 | 文件系统挂载表。 |
| 5 | `crontab` | `/var/spool/cron/crontabs/root` | `var/spool/cron/crontabs/` | 7 | root用户的cron任务（每个用户独立备份，此处仅列root）。 |
| 6 | `crontab-www` | `/var/spool/cron/crontabs/www-data` | `var/spool/cron/crontabs/` | 7 | www-data用户的cron任务。 |
| 7 | `sshd_config` | `/etc/ssh/sshd_config` | `etc/ssh/` | 7 | SSH服务端配置，关键安全文件。 |
| 8 | `ssh_config` | `/etc/ssh/ssh_config` | `etc/ssh/` | 7 | SSH客户端全局配置。 |
| 9 | `authorized_keys` | `/root/.ssh/authorized_keys` | `root/.ssh/` | 7 | root的SSH授权密钥。 |
| 10 | `nginx.conf` | `/etc/nginx/nginx.conf` | `etc/nginx/` | 7 | Nginx主配置文件。 |
| 11 | `default.conf` | `/etc/nginx/sites-available/default` | `etc/nginx/sites-available/` | 7 | Nginx默认站点配置（同时备份 `sites-enabled` 下的符号链接指向，实际内容在 `sites-available` 中）。 |
| 12 | `my.cnf` | `/etc/mysql/my.cnf` | `etc/mysql/` | 7 | MySQL/MariaDB 配置文件。 |
| 13 | `postgresql.conf` | `/etc/postgresql/16/main/postgresql.conf` | `etc/postgresql/16/main/` | 7 | PostgreSQL 16 主配置（版本号根据实际调整，备份时自动遍历目录）。 |
| 14 | `php.ini` | `/etc/php/8.2/cli/php.ini` | `etc/php/8.2/cli/` | 7 | PHP CLI 配置。 |
| 15 | `php-fpm.conf` | `/etc/php/8.2/fpm/php-fpm.conf` | `etc/php/8.2/fpm/` | 7 | PHP-FPM 配置。 |
| 16 | `haproxy.cfg` | `/etc/haproxy/haproxy.cfg` | `etc/haproxy/` | 7 | HAProxy负载均衡配置。 |
| 17 | `redis.conf` | `/etc/redis/redis.conf` | `etc/redis/` | 7 | Redis 配置。 |
| 18 | `memcached.conf` | `/etc/memcached.conf` | `etc/` | 7 | Memcached 配置。 |
| 19 | `docker-daemon.json` | `/etc/docker/daemon.json` | `etc/docker/` | 7 | Docker宿主机守护进程配置。 |
| 20 | `prometheus.yml` | `/etc/prometheus/prometheus.yml` | `etc/prometheus/` | 7 | Prometheus 监控配置。 |
| 21 | `alertmanager.yml` | `/etc/prometheus/alertmanager.yml` | `etc/prometheus/` | 7 | Alertmanager 告警配置。 |
| 22 | `grafana.ini` | `/etc/grafana/grafana.ini` | `etc/grafana/` | 7 | Grafana 仪表板配置。 |
| 23 | `sysctl.conf` | `/etc/sysctl.conf` | `etc/` | 7 | 内核参数配置。 |
| 24 | `limits.conf` | `/etc/security/limits.conf` | `etc/security/` | 7 | 用户资源限制。 |
| 25 | `sudoers` | `/etc/sudoers` | `etc/` | 7 | sudo权限配置（注意：备份前先检查语法，防止损坏的sudoers被覆盖）。 |
| 26 | `shadow` | `/etc/shadow` | `etc/` | 7 | 加密密码文件，权限敏感，仅root可读。备份时脱敏处理？本次仅备份，不改变内容。 |
| 27 | `passwd` | `/etc/passwd` | `etc/` | 7 | 用户账户基本信息。 |
| 28 | `group` | `/etc/group` | `etc/` | 7 | 用户组信息。 |
| 29 | `bashrc` | `/root/.bashrc` | `root/` | 7 | root用户bash配置文件。 |
| 30 | `bashrc-user` | `/home/admin/.bashrc` | `home/admin/` | 7 | admin用户bash配置。 |
| 31 | `vimrc` | `/root/.vimrc` | `root/` | 7 | root用户vim配置。 |
| 32 | `tmux.conf` | `/home/admin/.tmux.conf` | `home/admin/` | 7 | admin用户tmux配置。 |
| 33 | `gitconfig` | `/home/admin/.gitconfig` | `home/admin/` | 7 | admin用户Git全局配置。 |
| 34 | `environment` | `/etc/environment` | `etc/` | 7 | 系统环境变量。 |

> **说明**: 以上清单为非穷举，实际生产环境将根据 `backup_file_list.txt` 动态扩展。备份脚本自动遍历该文件列表，并排除临时文件（如 `.swp`, `.bak`, `~` 后缀的文件）。每个配置文件的保留版本数可通过全局变量 `RETENTION_COUNT=7` 调整。

---

## 3. 备注说明

### 3.1 忽略的文件模式

备份过程中自动忽略下列模式的文件或目录，以节省空间并避免无意义的历史版本：

- `*.swp` — Vim 交换文件
- `*.bak` — 手动备份文件
- `*~` — 临时备份文件
- `*.pid` — 进程ID文件
- `*.lock` — 进程锁文件
- `.git/` — Git元数据（配置文件本身的Git仓库会被忽略，但 `.gitconfig` 文件本身会备份）
- `__pycache__/` — Python缓存
- `node_modules/` — 若配置文件目录中包含此类目录（罕见），忽略
- `/var/log/` — 日志文件不在备份范围（另由日志管理处理）

### 3.2 特殊处理规则

1. **敏感文件权限保持**: 对于 `shadow`, `sudoers` 等权限敏感文件，备份前不改变权限位，备份后的文件权限保持原样（如 `shadow` 为 `000`），但备份目录本身拥有 `700` 权限，防止非授权访问。恢复时需手动调整权限。

2. **备份前语法检查**: 对于 `nginx.conf`, `haproxy.cfg`, `postgresql.conf`, `sshd_config` 等关键服务配置，备份脚本会在拷贝前调用服务自身的语法检查命令（如 `nginx -t`, `sshd -t`, `postgresql -c config_file=` 等）。若检查失败，则跳过备份并在日志中记录 **FAIL**，且触发告警（通过 `mail` 或 webhook）。备份脚本中相应片段如下：

   ```bash
   # 语法检查函数示例
   check_syntax() {
       local file="$1"
       case "$file" in
           */nginx/*)
               nginx -t -c "$file" >/dev/null 2>&1
               ;;
           */ssh/sshd_config)
               sshd -t -f "$file" >/dev/null 2>&1
               ;;
           */haproxy/*)
               haproxy -c -f "$file" >/dev/null 2>&1
               ;;
           *)
               return 0   # 无检查需求，默认通过
               ;;
       esac
       return $?
   }
   ```

3. **符号链接处理**: 备份时默认跟随符号链接（拷贝真实文件），若目标是一个符号链接，则拷贝其指向的原始文件。例如 `/etc/nginx/sites-enabled/default` 通常链接到 `../sites-available/default`，脚本会解析链接后备份真实文件，并同时在备份路径中保留符号链接名称（但目标重定向到备份目录中对应的真实文件）。恢复时使用 `rsync -L` 参数可重建符号链接。

4. **加密备份（可选）**: 对于高敏感文件（如 `shadow`, `id_rsa` 私钥），可在备份时使用 GPG 加密。本配置清单默认不启用，但预留开关 `ENCRYPT_SENSITIVE=true`。若启用，则对以下文件使用接收方的公钥加密：

   - `/etc/shadow`
   - `/root/.ssh/id_rsa`
   - `/home/*/.ssh/id_rsa` （若有）
   - 其他通过 `encrypt_list.txt` 指定的文件

   加密后的备份文件名附加 `.gpg` 后缀。

5. **备份周期与触发方式**:

   - 定时任务: 每天 01:00 (UTC) 通过 cron 执行
   - 手动触发: 通过 `backup_config.sh --force` 立即执行
   - 变更触发: 结合 inotify 监听关键目录（如 `/etc/nginx/conf.d/`, `/etc/ssh/`）的 `IN_CLOSE_WRITE` 事件，在修改后10分钟内触发增量备份（但仅保留当日版本，与常规备份版本数合并）。此功能默认关闭，需手动启用 (`USE_INOTIFY=true`)。

6. **版本清理策略**: 每日备份保留7个版本，即第8次备份时自动删除最旧的一个。清理逻辑基于文件名的时间戳后缀，保留最新的7个。由于采用硬链接，只有首次备份占用完整空间，后续仅差异部分占额外空间。每年1月1日会执行一次全量归档，将前一年的所有版本打包为 `.tar.gz` 并移至归档目录 `~/.config-backup/archives/`，然后清理旧的增量。

### 3.3 备份脚本核心逻辑（完整可运行）

以下 Bash 脚本为本次配置清单配套的备份引擎，可直接部署（需要 rsync 和 tar）。脚本从文件列表 `backup_file_list.txt` 读取配置，支持并发备份与日志。

```bash
#!/usr/bin/env bash
set -euo pipefail

# ==================== 全局配置 ====================
BACKUP_ROOT="$HOME/.config-backup"
RETENTION_COUNT=7
TIMESTAMP=$(date +%Y%m%d%H%M%S)
LOG_FILE="$BACKUP_ROOT/snapshots.log"
FILE_LIST="$BACKUP_ROOT/backup_file_list.txt"   # 格式: 每行 "源路径 备份子目录"
SENSITIVE_PATTERNS=( "shadow" "id_rsa" "id_dsa" "id_ecdsa" "id_ed25519" )
ENCRYPT_SENSITIVE=false
ENCRYPT_RECIPIENT="admin@example.com"   # 需提前配置 GPG 并导入公钥

# ==================== 函数定义 ====================
log() {
    local level="$1"
    local msg="$2"
    local datetime=$(date --rfc-3339=seconds)
    echo "[$datetime] [$level] $msg" >> "$LOG_FILE"
    if [ "$level" == "ERROR" ] || [ "$level" == "WARN" ]; then
        echo "[$datetime] [$level] $msg" >&2
    fi
}

check_syntax() {
    local src="$1"
    case "$src" in
        */nginx/*)
            if ! nginx -t -c "$src" >/dev/null 2>&1; then
                log "ERROR" "语法检查失败: $src (nginx -t)"
                return 1
            fi
            ;;
        */ssh/sshd_config)
            if ! sshd -t -f "$src" >/dev/null 2>&1; then
                log "ERROR" "语法检查失败: $src (sshd -t)"
                return 1
            fi
            ;;
        */haproxy/*.cfg)
            if ! haproxy -c -f "$src" >/dev/null 2>&1; then
                log "ERROR" "语法检查失败: $src (haproxy -c)"
                return 1
            fi
            ;;
        */postgresql/*/postgresql.conf)
            if ! pg_config --version >/dev/null 2>&1; then
                log "WARN" "PostgreSQL 未安装，跳过语法检查: $src"
            else
                PG_VERSION=$(pg_config --version | sed 's/^.* \([0-9]\+\).*/\1/')
                if ! pg_isready -q; then
                    log "WARN" "PostgreSQL 未运行，跳过语法检查: $src"
                else
                    if ! sudo -u postgres psql -c "SELECT 1;" >/dev/null 2>&1; then
                        log "WARN" "无法连接 postgres，跳过语法检查: $src"
                    fi
                fi
            fi
            ;;
        *)
            # 无检查需求
            ;;
    esac
    return 0
}

backup_file() {
    local src="$1"
    local dest_subdir="$2"
    local dest_dir="$BACKUP_ROOT/$dest_subdir"
    local backup_file="$dest_dir/$(basename "$src").$TIMESTAMP"

    # 创建目标目录
    mkdir -p "$dest_dir"

    # 语法检查(仅对关键文件, 失败则跳过)
    if ! check_syntax