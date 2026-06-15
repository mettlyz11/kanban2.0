# deployment_guide

> 任务: v9 #10 自动回滚 — 失败率升>15%自动git rollback
> 附件类型: 用户手册
> 生成时间: 2026-05-12 00:57

# v9 #10 自动回滚 — 失败率升>15%自动git rollback

## 用户手册

**文档版本**：1.0  
**发布日期**：2025-04-01  
**适用产品**：v9 部署流水线自动回滚组件（#10）  
**维护团队**：DevOps 自动化小组  

---

## 1. 前置条件

### 1.1 Git 仓库要求
- 仓库必须托管于 **GitHub、GitLab 或自托管的 Git 服务**（支持 HTTPS 或 SSH 协议）。
- 仓库需包含至少两个**稳定标签**（如 `v1.0.0`, `v1.0.1`）或一个已知的**上一个稳定提交 SHA**。回滚操作默认为 `HEAD^`（最近一次提交的前一个提交），也可以通过配置指向特定标签。
- 建议启用 **Git 保护分支**，避免直接 push 至 `main` 或 `master` 分支。脚本执行回滚时会强制推送，因此需要**写入权限**（详见 1.3 节）。

### 1.2 运行环境
| 组件           | 最低版本要求 | 推荐版本 |
|----------------|--------------|----------|
| Python         | 3.8+         | 3.11+    |
| Git CLI        | 2.20+        | 2.40+    |
| 操作系统       | Linux / macOS | Ubuntu 22.04 / macOS Ventura |
| 可选：Docker   | 20.10+       | 24.0+    |

依赖的 Python 模块（均内置或通过 `pip install` 安装）：
- `subprocess`（标准库）
- `os`, `sys`, `json`, `yaml`（如需读取 YAML 配置文件，需安装 `pyyaml`）
- `logging`
- `argparse`（如果使用 CLi 参数）

### 1.3 权限说明
- **Git 权限**：脚本运行时需要访问 git 仓库的**写权限**（用于推送回滚后的代码）。建议使用 **Personal Access Token (PAT)** 或 SSH key 认证。
- **文件系统权限**：脚本应部署在具有写入日志权限的目录，如 `/var/log/rollback/`。
- **执行权限**：脚本文件需设置可执行位（`chmod +x`）。
- **CI/CD 环境**：若集成到 Jenkins、GitLab CI 等，请确保 Runner 拥有对应仓库的 `maintainer` 或 `owner` 角色。

---

## 2. 配置文件示例

### 2.1 环境变量方式（推荐用于CI/CD）

创建 `.env` 文件（不应提交至代码仓库）：

```bash
# .env 文件
GIT_REPO_URL=https://github.com/your-org/your-app.git
GIT_BRANCH=main
GIT_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxxxx   # 仅在HTTPS时使用
ROLLBACK_THRESHOLD=15                  # 失败率百分比阈值
MAX_ROLLBACK_ATTEMPTS=3                # 单次部署允许的最大回滚次数
LOG_DIR=/var/log/rollback
WEBHOOK_URL=https://hooks.slack.com/services/XXX/YYY   # 可选：通知通道
MANUAL_CONFIRM_REQUIRED=false          # 是否需人工确认（true/false）
```

### 2.2 YAML 配置文件方式（适用于手动执行）

创建 `config.yaml`（需与脚本同目录或通过参数指定路径）：

```yaml
# config.yaml
repository:
  url: "https://github.com/your-org/your-app.git"
  branch: "main"
  token: "ghp_xxxxxxxxxxxxxxxxxxxxxx"   # 建议使用环境变量 GIT_TOKEN 覆盖
  # 或使用 SSH key（则省略 token）
  # ssh_key_path: "/home/user/.ssh/id_rsa"

rollback:
  threshold: 15                          # 百分比
  max_attempts: 3
  # 回滚目标：可选 "HEAD^" 或标签名
  target: "HEAD^"                        # 默认回退到上一个提交
  # target: "v1.0.1"                     # 也可指定标签

logging:
  directory: "/var/log/rollback"
  file: "auto_rollback.log"
  level: "INFO"                          # DEBUG, INFO, WARNING, ERROR

notification:
  enabled: true
  type: "slack"                          # 目前仅支持 slack
  webhook_url: "https://hooks.slack.com/services/XXX/YYY"

safety:
  manual_confirm: false                  # 若为true，则不会自动执行回滚，仅输出待执行命令
  max_daily_rollbacks: 5                 # 同一天内最大回滚次数（基于日志日期）
  allow_during_quiet_hours: false        # 是否允许在静默时段（如 22:00-06:00）执行回滚
  quiet_hours_start: "22:00"
  quiet_hours_end: "06:00"
```

若同时存在环境变量和 YAML 配置，**环境变量优先级更高**。

---

## 3. 安装步骤

### 3.1 获取脚本
将脚本文件 `auto_rollback.py`（见第 4 节完整代码）放在服务器指定路径，例如 `/opt/rollback/`：
```bash
sudo mkdir -p /opt/rollback
sudo chown $USER:$USER /opt/rollback
cp auto_rollback.py /opt/rollback/
chmod +x /opt/rollback/auto_rollback.py
```

### 3.2 安装 Python 依赖
如果使用了 `yaml` 模块，需安装 `pyyaml`：
```bash
pip install pyyaml
```

### 3.3 创建日志与状态目录
```bash
sudo mkdir -p /var/log/rollback
sudo mkdir -p /var/state/rollback
sudo chown $USER:$USER /var/log/rollback /var/state/rollback
```

### 3.4 初始化 Git 工作副本（可选）
如果脚本需要本地克隆仓库并重复使用，可预先克隆：
```bash
cd /opt/rollback
git clone https://github.com/your-org/your-app.git workdir
cd workdir
git checkout main
```
如果不预先克隆，脚本会每次在临时目录中克隆并删除。

---

## 4. 运行方式

### 4.1 命令行直接执行

```bash
# 使用 YAML 配置文件
python /opt/rollback/auto_rollback.py --config /path/to/config.yaml

# 使用环境变量（脚本自动读取 .env 或系统环境变量）
python /opt/rollback/auto_rollback.py

# 指定自定义参数覆盖
python /opt/rollback/auto_rollback.py --threshold 20 --max-attempts 2 --log-dir /tmp/log
```

参数帮助：
```
usage: auto_rollback.py [-h] [--config CONFIG] [--threshold THRESHOLD]
                        [--max-attempts MAX_ATTEMPTS] [--log-dir LOG_DIR]
                        [--dry-run] [--version]

Auto rollback script for v9 #10

optional arguments:
  -h, --help            show this help message and exit
  --config CONFIG       Path to YAML config file
  --threshold THRESHOLD Failure rate threshold (percent)
  --max-attempts MAX_ATTEMPTS
                        Max rollback attempts per deployment
  --log-dir LOG_DIR     Directory for log files
  --dry-run             Simulate rollback without actual git operations
  --version             Show script version and exit
```

### 4.2 集成到 CI/CD 管道

#### 示例：GitLab CI（.gitlab-ci.yml 片段）

```yaml
stages:
  - deploy
  - health-check
  - rollback

variables:
  ROLLBACK_THRESHOLD: "15"
  MAX_ATTEMPTS: "3"

auto-rollback:
  stage: rollback
  script:
    - python /opt/rollback/auto_rollback.py --threshold $ROLLBACK_THRESHOLD --max-attempts $MAX_ATTEMPTS
  only:
    - main
  when: on_failure   # 仅在部署阶段失败时触发
```

#### 示例：Jenkins Pipeline（Jenkinsfile 片段）

```groovy
pipeline {
    agent any
    environment {
        GIT_REPO_URL = 'https://github.com/your-org/your-app.git'
        GIT_BRANCH = 'main'
        ROLLBACK_THRESHOLD = '15'
    }
    stages {
        stage('Deploy') {
            steps {
                // 实际部署步骤（略）
            }
        }
        stage('Health Check') {
            steps {
                // 监测失败率，若超过阈值则触发回滚
                script {
                    def failureRate = sh(script: 'curl -s http://localhost:8080/metrics | grep failure_rate | awk \'{print $2}\'', returnStdout: true).trim()
                    if (failureRate.toFloat() > env.ROLLBACK_THRESHOLD.toFloat()) {
                        sh 'python /opt/rollback/auto_rollback.py'
                    }
                }
            }
        }
    }
}
```

### 4.3 定时运行（cron 任务）
如果希望定期检测失败率并自动回滚，可设置 cron：
```bash
# 每5分钟执行一次检测（配置文件中需指定动态获取失败率的逻辑）
*/5 * * * * cd /opt/rollback && python auto_rollback.py --config config.yaml
```
注意：频繁回滚可能导致不稳定，建议 cron 模式与 CI/CD 触发模式只选择一种。

---

## 5. 完整可运行脚本代码

以下是 `auto_rollback.py` 的完整实现（Python 3.8+）：

```python
#!/usr/bin/env python3
"""
v9 #10 Auto Rollback Script
当部署失败率超过阈值时，自动执行 git rollback 到上一个稳定版本。
支持环境变量与 YAML 配置文件，内置安全机制与详细日志。
"""

import os
import sys
import json
import logging
import subprocess
import datetime
import argparse
import tempfile
import shutil
from pathlib import Path

# 尝试加载 pyyaml（可选）
try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

__version__ = "1.0.0"

# ---------- 默认配置 ----------
DEFAULT_CONFIG = {
    "repository": {
        "url": None,
        "branch": "main",
        "token": None,
        "ssh_key_path": None,
    },
    "rollback": {
        "threshold": 15,
        "max_attempts": 3,
        "target": "HEAD^",
    },
    "logging": {
        "directory": "/var/log/rollback",
        "file": "auto_rollback.log",
        "level": "INFO",
    },
    "notification": {
        "enabled": False,
        "type": "slack",
        "webhook_url": None,
    },
    "safety": {
        "manual_confirm": False,
        "max_daily_rollbacks": 5,
        "allow_during_quiet_hours": False,
        "quiet_hours_start": "22:00",
        "quiet_hours_end": "06:00",
    }
}

# ---------- 辅助函数 ----------

def load_config(args):
    """合并环境变量、YAML 文件与命令行参数，返回最终配置字典。"""
    config = DEFAULT_CONFIG.copy()

    # 1. 从文件加载（覆盖默认）
    if args.config and Path(args.config).exists():
        if not HAS_YAML:
            logging.error("pyyaml 未安装，无法读取 YAML 配置文件。请运行 pip install pyyaml")
            sys.exit(1)
        with open(args.config, 'r') as f:
            file_config = yaml.safe_load(f)
        if file_config:
            deep_merge(config, file_config)

    # 2. 环境变量覆盖（优先级更高）
    env_map = {
        "GIT_REPO_URL": ("repository", "url"),
        "GIT_BRANCH": ("repository", "branch"),
        "GIT_TOKEN": ("repository", "token"),
        "ROLLBACK_THRESHOLD": ("rollback", "threshold"),
        "MAX_ROLLBACK_ATTEMPTS": ("rollback", "max_attempts"),
        "LOG_DIR": ("logging", "directory"),
        "MANUAL_CONFIRM_REQUIRED": ("safety", "manual_confirm"),
    }
    for env_name, (section, key) in env_map.items():
        value = os.environ.get(env_name)
        if value is not None:
            # 类型转换
            if key == "threshold":
                value = int(value)
            elif key == "max_attempts":
                value = int(value)
            elif key == "manual_confirm":
                value = value.lower() in ("true", "1", "yes")
            config[section][key] = value

    # 3. 命令行参数覆盖
    if args.threshold is not None:
        config["rollback"]["threshold"] = args.threshold
    if args.max_attempts is not None:
        config["rollback"]["max_attempts"] = args.max_attempts
    if args.log_dir is not None:
        config["logging"]["directory"] = args.log_dir
    # dry-run 模式
    config["_dry_run"] = args.dry_run

    return config

def deep_merge(base, override):
    """递归合并字典（override 中非 None 值覆盖 base）。"""
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            deep_merge(base[key], value)
        else:
            if value is not None:
                base[key] = value

def setup_logging(config):
    """配置日志输出：控制台 + 文件。"""
    log_dir = config["logging"]["directory"]
    log_file = config["logging"]["file"]
    level_name = config["logging"]["level"].upper()
    level = getattr(logging, level_name, logging.INFO)

    os.makedirs(log_dir, exist_ok=True)

    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    logger = logging.getLogger("auto_rollback")
    logger.setLevel(level)

    # 移除已有处理器避免重复
    logger.handlers.clear()

    # 文件处理器
    fh = logging.FileHandler(os.path.join(log_dir, log_file))
    fh.setFormatter(formatter)
    logger.addHandler(fh)

    # 控制台处理器
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    return logger

def run_git_command(cmd, cwd=None, env=None):
    """执行 git 命令并返回输出与状态。"""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=120,
            env=env
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", "Command timed out"
    except Exception as e:
        return -1, "", str(e)

def get_failure_rate(config, logger):
    """
    获取当前部署的失败率。
    此处演示模拟数据（生产环境中应接入监控API，如 Prometheus）。
    返回失败率百分比（float）。
    """
    # TODO: 替换为真实监控查询
    # 模拟：生成 0~30 之间的随机数作为演示
    import random
    rate = random.uniform(0, 30)
    logger.info(f"当前失败率 (模拟): {rate:.2f}%")
    return rate

def check_safety_guards(config, logger):
    """
    检查安全限制：每日回滚次数、静默时段。
    返回 (允许执行: bool, 拒绝原因: str)。
    """
    if config["safety"]["manual_confirm"]:
        logger.warning("MANUAL_CONFIRM_REQUIRED 为 true，不会自动执行回滚。等待人工操作。")
        return False, "Manual confirm required"

    # 每日回滚次数限制
    log_dir = config["logging"]["directory"]
    today = datetime.date.today().isoformat()
    state_file = os.path.join(log_dir, f"rollback_count_{today}.txt")
    count = 0
    if os.path.exists(state_file):
        with open(state_file, 'r') as f:
            count = int(f.read().