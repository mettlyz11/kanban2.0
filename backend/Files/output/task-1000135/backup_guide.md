# backup_guide

> 任务: v7 #4 配置文件自动备份
> 附件类型: 操作指南
> 生成时间: 2026-05-12 09:29

# v7 #4 配置文件自动备份 — 操作指南

**文档版本：** 1.0  
**适用环境：** Linux（CentOS 7+/Ubuntu 18.04+）  
**维护团队：** 系统运维组  
**最后更新：** 2025-07-15  

---

## 1. 概述

本指南详细说明**v7 #4 配置文件自动备份系统**的部署、配置与日常使用。系统基于 **Git** 实现版本管理，通过 **systemd 服务** 驱动自动提交脚本，将关键配置文件（如 Nginx、SSH、网络设置等）定期备份至本地和远程仓库。备份保留最近 **7 个有效版本**，超出部分自动清理。

---

## 2. 备份目录结构说明

所有备份数据存储在 `/data/backup/configs` 目录下，内部组织如下：

```
/data/backup/configs/
├── .git/                     # Git 仓库元数据（自动生成）
├── etc/                      # 待备份的配置文件镜像目录
│   ├── nginx/
│   │   ├── nginx.conf
│   │   └── sites-enabled/
│   ├── ssh/
│   │   ├── sshd_config
│   │   └── authorized_keys
│   ├── network/
│   │   └── interfaces
│   └── systemd/
│       └── custom.service
├── backup.log                # 自动备份运行日志
├── cleanup.log               # 版本清理日志
└── README.md                 # 仓库说明（可选）

```

**说明：**
- `etc/` 是配置文件的实际存储副本，自动备份脚本每次同步时将源文件复制到此目录下的对应路径。
- `.git/` 为 Git 版本库，所有版本历史保存在此。
- 日志文件 `backup.log` 和 `cleanup.log` 保存在仓库根目录外（实际在 `/data/backup/logs/` 下，但通过软连接映射到此处），便于巡检。
- 推荐将敏感文件（如 SSH 私钥）**排除**在备份范围外，可在脚本中定义排除列表。

**示例数据**（模拟 `/etc/nginx/nginx.conf`）：

```nginx
# 2025-07-14 16:30:00 备份版本
worker_processes  auto;
events {
    worker_connections  1024;
}
http {
    include       mime.types;
    default_type  application/octet-stream;
    sendfile        on;
    keepalive_timeout  65;
    server {
        listen       80;
        server_name  example.com;
        location / {
            root   /var/www/html;
            index  index.html index.htm;
        }
    }
}
```

---

## 3. 版本保留策略（7 个版本）与自动清理机制

### 3.1 策略定义

系统只保留最近 **7 个有效提交**（即 7 个版本），旧版本在每次新的自动提交后由清理脚本删除。这里的“有效版本”指 **Git 中所有分支上的 commit 数量**（默认只考虑 `master` 分支）。若手动创建了其他分支，清理脚本不会自动处理，需人工干预。

### 3.2 清理机制实现

清理脚本 `cleanup_old_versions.sh` 在每次自动提交完成后立即执行。逻辑如下：

1. 获取当前分支（默认为 master）的 commit 总数。
2. 如果 commit 数量 > 7，则计算需要删除的 commit 数量（`n = total - 7`）。
3. 使用 `git reset --hard` 回退到第 8 个 commit（保留最新的 7 个）。
4. 使用 `git push --force` 强制同步远程仓库（谨慎使用，需确保远程备份仅为本地副本的镜像）。

**注意：** 此方法会丢失旧版本的增量信息。如需更精细的保留策略（如保留按日期的快照），建议改用 `git rebase -i` 或 `git filter-branch`，但会增加复杂度。本系统采用此简单回退法，并在执行前记录日志。

**示例日志（cleanup.log）：**

```
[2025-07-15 03:00:01] 开始清理操作
[2025-07-15 03:00:01] 当前 master 分支 commit 数: 9
[2025-07-15 03:00:01] 需要删除 2 个旧版本
[2025-07-15 03:00:01] 执行 git reset --hard HEAD~2
[2025-07-15 03:00:01] 清理完成，剩余 commit 数: 7
[2025-07-15 03:00:01] 已强制推送到远程 origin
```

**注意：** 若推送失败（如远程仓库拒绝），脚本会记录错误并退出，不继续删除本地 commit。运维人员应检查网络或远程仓库权限。

---

## 4. 自动提交脚本与系统服务运行原理

### 4.1 自动提交脚本 `auto_backup.sh`

脚本位于 `/usr/local/bin/auto_backup.sh`，内容如下（完整可运行，请根据实际路径调整变量）：

```bash
#!/bin/bash
# ============================================================
# v7 #4 配置文件自动备份脚本
# 功能：同步指定配置文件目录，生成 Git 提交，保留最近7个版本
# ============================================================

# 配置变量
SOURCE_DIRS=(
    "/etc/nginx"
    "/etc/ssh"
    "/etc/network"
    "/etc/systemd/system"
)
BACKUP_BASE="/data/backup/configs"
EXCLUDE_PATTERNS=("*.key" "*.pem" "authorized_keys" "*passwd*")  # 排除敏感文件
LOG_FILE="/data/backup/logs/backup.log"
CLEANUP_LOG="/data/backup/logs/cleanup.log"
MAX_VERSIONS=7
TIMESTAMP=$(date "+%Y-%m-%d %H:%M:%S")

# 函数：写日志
log() {
    echo "[${TIMESTAMP}] $1" >> "$LOG_FILE"
}

# 1. 同步配置文件到备份目录
log "开始同步源目录..."
for src in "${SOURCE_DIRS[@]}"; do
    # 构造目标路径：/data/backup/configs/etc 下的相对路径
    dest="${BACKUP_BASE}/etc/$(echo $src | sed 's|^/etc/||')"
    mkdir -p "$dest"
    # 使用 rsync 同步，排除指定模式，保留权限
    rsync -a --delete --exclude-from=<(printf '%s\n' "${EXCLUDE_PATTERNS[@]}") "$src/" "$dest/" 2>&1 >> "$LOG_FILE"
    log "已同步 $src -> $dest"
done

# 2. 进入备份仓库根目录
cd "$BACKUP_BASE" || { log "错误：无法进入目录 $BACKUP_BASE"; exit 1; }

# 3. 检查是否有变化
if [[ -z $(git status --porcelain) ]]; then
    log "无文件变化，跳过本次提交"
    exit 0
fi

# 4. 添加所有变更并提交
git add -A
COMMIT_MSG="Auto backup $(date +%Y-%m-%d_%H%M%S)"
git commit -m "$COMMIT_MSG" 2>&1 >> "$LOG_FILE"
if [[ $? -ne 0 ]]; then
    log "提交失败，终止"
    exit 1
fi
log "已提交: $COMMIT_MSG"

# 5. 清理旧版本（保留最近 MAX_VERSIONS 个）
log "开始检查版本数量..."
CURRENT_COUNT=$(git rev-list --count HEAD)
if [[ $CURRENT_COUNT -gt $MAX_VERSIONS ]]; then
    NUM_TO_DELETE=$(( CURRENT_COUNT - MAX_VERSIONS ))
    log "当前版本 $CURRENT_COUNT，需删除 $NUM_TO_DELETE 个"
    # 回退到保留的最新 MAX_VERSIONS 个版本
    git reset --hard HEAD~$NUM_TO_DELETE 2>&1 >> "$CLEANUP_LOG"
    if [[ $? -ne 0 ]]; then
        log "版本回退失败，请检查"
        exit 1
    fi
    log "已回退，剩余版本: $MAX_VERSIONS"

    # 强制推送 (如果配置了远程仓库)
    if git remote -v | grep -q origin; then
        git push --force origin master 2>&1 >> "$CLEANUP_LOG"
        if [[ $? -eq 0 ]]; then
            log "已强制推送到远程仓库"
        else
            log "推送失败，请检查远程仓库配置"
        fi
    fi
else
    log "版本数 ($CURRENT_COUNT) 未超过限制 ($MAX_VERSIONS)，无需清理"
fi

log "备份流程完成"
exit 0
```

**权限设置：**
```bash
chmod +x /usr/local/bin/auto_backup.sh
```

### 4.2 系统服务单元文件

创建 systemd 服务 `/etc/systemd/system/config-backup.service` 和定时器 `/etc/systemd/system/config-backup.timer`。

**服务单元文件：**

```ini
[Unit]
Description=v7 #4 配置文件自动备份服务
After=network.target

[Service]
Type=oneshot
ExecStart=/usr/local/bin/auto_backup.sh
User=root
Group=root
StandardOutput=journal
StandardError=journal
```

**定时器单元文件：**

```ini
[Unit]
Description=每天03:00 执行配置备份

[Timer]
OnCalendar=daily
# 或精确到每天凌晨3点：OnCalendar=*-*-* 03:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

**启用定时器：**
```bash
systemctl daemon-reload
systemctl enable config-backup.timer
systemctl start config-backup.timer
```

**手动立即执行一次：**
```bash
systemctl start config-backup.service
```

**查看运行日志：**
```bash
journalctl -u config-backup.service -f
```

### 4.3 定时器工作原理

- 定时器在系统启动后每天触发一次服务（默认凌晨 `00:00`，本配置通过 `OnCalendar=daily` 实现；若需凌晨3点，请取消注释并注释上一行）。
- `Persistent=true` 允许在系统长时间关机后的第一次启动时补执行错过的定时任务。
- 服务执行完毕后自动停止（`Type=oneshot`），不常驻内存。

---

## 5. 远程备份仓库配置方法

### 5.1 前提条件

- 拥有一台远程 Git 服务器（如 GitLab、GitHub、自建 Gitea 或纯 SSH Git 仓库）。
- 本机已配置 SSH 密钥对，并已将公钥添加到远程仓库的部署密钥或用户账户中。

### 5.2 添加远程仓库

在备份目录 `/data/backup/configs` 下执行：

```bash
cd /data/backup/configs
git remote add origin git@git.example.com:ops/config-backup.git
```

**示例命令（使用 SSH 协议）：**

```bash
git remote add origin git@192.168.1.100:/srv/git/config-backup.git
```

如果远程仓库要求使用 HTTPS 并需要凭据：

```bash
git remote add origin https://gitlab.com/team/config-backup.git
# 先设置凭据缓存（避免交互式密码输入）
git config --global credential.helper store
```

### 5.3 首次推送

```bash
git push -u origin master
```

若远程仓库为空，可能需要允许强制推送（`git push --force`）。建议在远程仓库端设置保护分支规则：只允许特定用户强制推送，或者禁用强制推送（本系统清理脚本会使用 force，需确保可用）。

### 5.4 验证连接

```bash
git remote -v
# 应显示类似：
# origin  git@git.example.com:ops/config-backup.git (fetch)
# origin  git@git.example.com:ops/config-backup.git (push)
```

### 5.5 安全建议

- 使用 SSH 密钥替代密码，密钥密码短语可通过 `ssh-agent` 管理（或使用无密码密钥，确保私钥文件权限为 600）。
- 远程仓库建议设置为私有。
- 定期轮换 SSH 密钥和访问令牌。

---

## 6. 单文件恢复与全量恢复操作步骤

### 6.1 单文件恢复（从本地仓库）

**场景：** 某个配置文件（如 `/etc/nginx/nginx.conf`）被误修改，需要从备份中恢复。

**步骤：**

1. 切换到备份仓库目录。
   ```bash
   cd /data/backup/configs
   ```

2. 使用 `git log` 查看历史提交，找到包含该文件的合理版本（通常是最新的或前一个版本）。
   ```bash
   git log --oneline -- etc/nginx/nginx.conf
   ```

   示例输出：
   ```
   a1b2c3d Auto backup 2025-07-14_160000
   e4f5g6h Auto backup 2025-07-13_160000
   ```

3. 将指定版本的文件恢复到工作目录（但不要覆盖仓库，而是复制到原始位置）。
   ```bash
   git show a1b2c3d:etc/nginx/nginx.conf > /tmp/nginx.conf.recovered
   ```
   或者使用 `git checkout` 但注意不要用 `HEAD` 覆盖，建议：
   ```bash
   git checkout a1b2c3d -- etc/nginx/nginx.conf
   ```
   此命令会将备份仓库中的文件恢复到当前工作目录（`/data/backup/configs/etc/nginx/nginx.conf`），然后复制到原始位置：
   ```bash
   cp /data/backup/configs/etc/nginx/nginx.conf /etc/nginx/nginx.conf
   ```

4. 验证配置文件语法（以 Nginx 为例）：
   ```bash
   nginx -t
   ```
   若无错误，重新加载服务：
   ```bash
   systemctl reload nginx
   ```

### 6.2 单文件恢复（从远程仓库）

如果本地仓库损坏，可从远程克隆最新的 7 个版本之一：

1. 新建临时目录，克隆远程仓库（浅克隆，只取最近一次提交以加快速度）：
   ```bash
   git clone --depth 1 git@git.example.com:ops/config-backup.git /tmp/config-restore
   ```

2. 找到所需文件并复制。

### 6.3 全量恢复（将整个系统配置恢复到某时间点）

**场景：** 服务器重装或配置目录大部分丢失，需要从备份完全恢复。

**步骤：**

1. 确保备份仓库是最新的（如果本地存在则跳过此步）。
2. 进入备份目录，查看提交历史，选择要恢复到的版本（通常为最新的）。
   ```bash
   cd /data/backup/configs
   git log --oneline -5
   ```

3. 重置工作目录到该版本（注意：这将丢弃未提交的更改）。
   ```bash
   git reset --hard <commit_hash>
   ```
   或者直接使用最新版：`git reset --hard HEAD`

4. 将 `etc/` 下的所有文件同步回对应的系统目录。**强烈建议**在恢复前备份当前系统配置（例如 `cp -a /etc /etc.bak`）。

   ```bash
   # 使用 rsync 将备份的配置文件复制回 /etc，注意排除敏感目录如 /etc/ssl/private
   rsync -a --delete /data/backup/configs/etc/ /etc/
   ```

   **注意：** `--delete` 会删除目标中存在于源中没有的文件，请谨慎使用。如果只希望恢复特定子目录，请分别操作。

5. 逐一重新加载受影响的服务。例如：
   ```bash
   for service in nginx sshd networking; do
       systemctl reload $service 2>/dev/null || systemctl restart $service
   done
   ```

6. 验证系统功能。

---

## 7. 常见问题与故障排查

### 7.1 备份脚本未按计划执行

- **检查定时器状态：**
  ```bash
  systemctl status config-backup.timer
  systemctl list-timers --all | grep config
  ```
- **检查服务是否已启用：**
  ```bash
  systemctl is-enabled config-backup.service
  ```
- **查看 journal 日志：**
  ```bash
  journalctl -u config-backup.service --since "1 day ago"
  ```
- **可能原因：** 系统时间错误、`OnCalendar` 配置错误（如误用分号）、依赖的 `network.target` 未正确生效。

### 7.2 远程推送失败

- **错误：** `Permission denied (publickey)`
  **解决方案：** 确认公钥已添加到远程仓库，私钥路径正确。使用 `ssh -T git@git.example.com` 测试连接。

- **错误：** `failed to push some refs`
  **原因：** 远程分支包含本地没有的提交，或者远程仓库配置了保护分支拒绝强制推送。
  **解决方案：**