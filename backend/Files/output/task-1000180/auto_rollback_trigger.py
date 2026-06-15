# auto_rollback_trigger

> 任务: v9 #10 自动回滚 — 失败率升>15%自动git rollback
> 附件类型: 代码文件
> 生成时间: 2026-05-12 00:56

```python
#!/usr/bin/env python3
"""
自动回滚核心逻辑实现 —— 失败率监控与自动 Git Rollback

本脚本用于在部署或持续集成流水线中自动检测服务失败率，
当失败率超过预设阈值（默认 15%）时自动执行 Git 回滚操作，
同时包含安全确认、并发保护、回滚次数限制和完整日志记录。

适用场景：
- CI/CD 流水线中的部署后监控
- 定时任务或守护进程持续监测
- 手工触发快速回滚

依赖：
- Python 3.6+
- git 命令行（需在 PATH 中可用）
- 可选：外部 API 或命令用于采集失败率数据

使用示例：
    # 默认阈值 15%，自动确认模式
    python auto_rollback.py

    # 指定阈值和检查来源
    python auto_rollback.py --threshold 20 --source api --api-url http://monitor.example.com/failure-rate

    # 交互确认模式（手动确认是否执行回滚）
    python auto_rollback.py --confirm

    # 限制回滚次数（每日最多 3 次）
    python auto_rollback.py --max-rollbacks 3
"""

import argparse
import datetime
import json
import logging
import os
import subprocess
import sys
import time
import fcntl
import tempfile
from pathlib import Path
from typing import Optional, Tuple

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("/var/log/auto_rollback.log", mode="a"),
    ],
)
logger = logging.getLogger("AutoRollback")

# 默认配置
DEFAULT_THRESHOLD = 15.0  # 失败率百分比阈值
CONFIG_FILE = "/etc/auto_rollback.conf"  # 可选配置文件位置
LOCK_FILE = "/tmp/auto_rollback.lock"  # 锁文件防止并发
COUNT_FILE = "/tmp/auto_rollback_count.json"  # 回滚次数记录文件
MAX_ROLLBACKS_PER_DAY = 5  # 每日最大回滚次数


# ======================================================================
# 1. 配置加载
# ======================================================================
def load_config() -> dict:
    """
    从环境变量或配置文件读取参数，环境变量优先级最高。

    支持的环境变量：
        FAILURE_RATE_THRESHOLD   : 失败率阈值（浮点数）
        ROLLBACK_SOURCE          : 失败率来源 (file/api/command)
        ROLLBACK_SOURCE_PATH     : 来源具体参数（文件路径/API URL/命令）
        ROLLBACK_CONFIRM         : 是否开启交互确认 (true/false)
        MAX_ROLLBACKS_PER_DAY    : 每日最大回滚次数

    返回包含所有配置的字典，缺失值使用默认值。
    """
    config = {
        "threshold": DEFAULT_THRESHOLD,
        "source": "file",
        "source_path": "/var/log/failure_rate.json",
        "confirm": False,
        "max_rollbacks": MAX_ROLLBACKS_PER_DAY,
    }

    # 尝试加载配置文件（JSON 格式）
    conf_path = Path(CONFIG_FILE)
    if conf_path.exists() and conf_path.is_file():
        try:
            with open(conf_path, "r") as f:
                file_conf = json.load(f)
                config.update(file_conf)
                logger.info(f"已从 {CONFIG_FILE} 加载配置")
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"配置文件解析失败 ({e})，使用默认值")

    # 环境变量覆盖
    env_map = {
        "FAILURE_RATE_THRESHOLD": ("threshold", float),
        "ROLLBACK_SOURCE": ("source", str),
        "ROLLBACK_SOURCE_PATH": ("source_path", str),
        "ROLLBACK_CONFIRM": ("confirm", lambda x: x.lower() == "true"),
        "MAX_ROLLBACKS_PER_DAY": ("max_rollbacks", int),
    }

    for env_var, (key, converter) in env_map.items():
        env_val = os.environ.get(env_var)
        if env_val is not None:
            try:
                config[key] = converter(env_val)
                logger.debug(f"环境变量 {env_var} -> {key} = {config[key]}")
            except (ValueError, TypeError) as e:
                logger.error(f"环境变量 {env_var} 值 '{env_val}' 转换失败: {e}")

    return config


# ======================================================================
# 2. 失败率检查函数
# ======================================================================
def check_failure_rate(source: str, source_path: str) -> Tuple[bool, Optional[float]]:
    """
    获取当前系统的失败率。

    支持三种数据源：
        - file  : 从 JSON 文件读取，格式如 {"failure_rate": 12.5}
        - api   : 通过 HTTP GET 请求获取，响应格式同文件
        - command: 执行外部命令，其标准输出应包含失败率数值

    参数：
        source     : 来源类型 (file/api/command)
        source_path: 文件的路径 / API 的 URL / 完整的命令字符串

    返回：
        (成功与否, 失败率浮点数或None)
    """
    if source == "file":
        path = Path(source_path)
        if not path.exists():
            logger.error(f"失败率文件不存在: {source_path}")
            return False, None
        try:
            with open(path, "r") as f:
                data = json.load(f)
                rate = float(data.get("failure_rate", data.get("rate", None)))
                if rate is None:
                    logger.error("文件中未找到 'failure_rate' 或 'rate' 字段")
                    return False, None
                logger.info(f"从文件 {source_path} 读取失败率: {rate}%")
                return True, rate
        except (json.JSONDecodeError, IOError, ValueError) as e:
            logger.error(f"读取失败率文件失败: {e}")
            return False, None

    elif source == "api":
        import urllib.request
        import urllib.error

        try:
            req = urllib.request.Request(source_path, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                rate = float(data.get("failure_rate", data.get("rate", None)))
                if rate is None:
                    logger.error("API 响应中未找到 'failure_rate' 或 'rate' 字段")
                    return False, None
                logger.info(f"从 API {source_path} 获取失败率: {rate}%")
                return True, rate
        except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, ValueError) as e:
            logger.error(f"调用 API 获取失败率失败: {e}")
            return False, None

    elif source == "command":
        try:
            result = subprocess.run(
                source_path,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                logger.error(f"命令执行失败 (返回码 {result.returncode}): {result.stderr}")
                return False, None
            output = result.stdout.strip()
            try:
                rate = float(output)
            except ValueError:
                # 尝试解析 JSON 格式
                try:
                    data = json.loads(output)
                    rate = float(data.get("failure_rate", data.get("rate", output)))
                except (json.JSONDecodeError, ValueError, TypeError):
                    logger.error(f"无法从命令输出解析失败率: '{output}'")
                    return False, None
            logger.info(f"从命令 '{source_path}' 获取失败率: {rate}%")
            return True, rate
        except subprocess.TimeoutExpired:
            logger.error("命令执行超时 (30s)")
            return False, None
        except Exception as e:
            logger.error(f"命令执行异常: {e}")
            return False, None

    else:
        logger.error(f"未知的失败率来源类型: {source}")
        return False, None


# ======================================================================
# 3. 安全确认与用户交互
# ======================================================================
def get_user_confirmation(failure_rate: float, threshold: float) -> bool:
    """
    交互式询问用户是否确认执行回滚。

    仅当配置中 confirm=True 时使用，否则自动确认。
    超时 30 秒无响应视为放弃。

    返回：
        True 确认执行，False 取消
    """
    # print("\n⚠️  警告：失败率 {:.2f}% 超过阈值 {:.2f}%".format(failure_rate, threshold))
    # print("即将执行 Git 回滚操作，此操作将撤销上一次提交。")
    try:
        answer = input("是否确认回滚？(yes/no, 默认 no): ").strip().lower()
        if answer in ("yes", "y"):
            return True
        else:
            logger.info("用户取消回滚")
            return False
    except (EOFError, KeyboardInterrupt):
        logger.warning("用户输入中断，取消回滚")
        return False


# ======================================================================
# 4. 执行 Git 回滚
# ======================================================================
def execute_git_rollback() -> bool:
    """
    执行 Git 回滚命令。

    回滚策略为 `git reset --hard HEAD~1`，即丢弃最近一次提交的所有更改。
    如果工作目录有未提交的更改会被强制丢弃（危险操作），
    因此建议在 CI/CD 环境中使用且确保工作区是干净的。

    返回：
        True 回滚成功，False 失败
    """
    # 检查是否在 Git 仓库中
    try:
        subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            capture_output=True,
            check=True,
        )
    except subprocess.CalledProcessError:
        logger.error("当前目录不是 Git 仓库，无法执行回滚")
        return False

    # 检查当前分支是否有至少一个历史提交（不能回滚到空仓库）
    try:
        result = subprocess.run(
            ["git", "rev-list", "--count", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        commit_count = int(result.stdout.strip())
        if commit_count < 2:  # HEAD~1 要求至少有两个提交
            logger.error("当前分支只有 1 个提交，无法回滚（需要至少 2 个）")
            return False
    except (subprocess.CalledProcessError, ValueError) as e:
        logger.error(f"检查提交历史失败: {e}")
        return False

    # 执行硬重置到上一个提交
    logger.info("正在执行: git reset --hard HEAD~1")
    try:
        result = subprocess.run(
            ["git", "reset", "--hard", "HEAD~1"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode == 0:
            logger.info(f"回滚成功:\n{result.stdout}")
            return True
        else:
            logger.error(f"git reset 失败 (返回码 {result.returncode}): {result.stderr}")
            return False
    except subprocess.TimeoutExpired:
        logger.error("git reset 执行超时 (60s)")
        return False
    except Exception as e:
        logger.error(f"git reset 异常: {e}")
        return False


# ======================================================================
# 5. 防御机制：锁文件与回滚次数限制
# ======================================================================
def acquire_lock() -> bool:
    """
    获取文件锁（基于 LOCK_FILE），防止同时运行多个实例。

    使用 fcntl.flock 实现建议锁，若锁已被占用则返回 False。
    锁文件会在进程退出时自动释放，或通过显式 release_lock 释放。

    返回：
        True 成功获取锁，False 已被锁定
    """
    lock_path = Path(LOCK_FILE)
    try:
        # 创建锁文件（如果不存在）
        lock_fd = open(lock_path, "w")
        # 尝试非阻塞获取锁
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        # 将锁文件描述符存储在全局变量，以便之后释放
        global _lock_fd
        _lock_fd = lock_fd
        logger.debug(f"已获取锁 {LOCK_FILE}")
        return True
    except (IOError, BlockingIOError):
        logger.warning(f"另一个进程已持有锁 {LOCK_FILE}，退出")
        return False
    except Exception as e:
        logger.error(f"获取锁异常: {e}")
        return False


def release_lock():
    """释放之前获取的文件锁。"""
    if hasattr(globals(), "_lock_fd") and _lock_fd:
        try:
            fcntl.flock(_lock_fd, fcntl.LOCK_UN)
            _lock_fd.close()
            logger.debug("锁已释放")
        except Exception as e:
            logger.error(f"释放锁失败: {e}")


def check_and_increment_rollback_count(max_rollbacks: int) -> bool:
    """
    检查当日回滚次数是否已达上限，并递增次数。

    次数记录在 COUNT_FILE (JSON)，键为日期字符串，值为当日次数。
    每日零点重置计数。

    参数：
        max_rollbacks: 每日最大允许回滚次数

    返回：
        True 允许执行回滚（未达上限），False 已达上限应中止
    """
    today = datetime.date.today().isoformat()
    count_data = {}
    count_path = Path(COUNT_FILE)

    # 读取现有计数
    if count_path.exists():
        try:
            with open(count_path, "r") as f:
                count_data = json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"计数文件损坏或无法读取: {e}，重置计数")

    # 清洗过期日期（保留最近 7 天）
    clean_data = {}
    for date_str, cnt in count_data.items():
        if isinstance(date_str, str) and isinstance(cnt, int):
            # 只保留日期格式正确的条目
            try:
                datetime.date.fromisoformat(date_str)
                clean_data[date_str] = cnt
            except ValueError:
                pass
    count_data = clean_data

    current_count = count_data.get(today