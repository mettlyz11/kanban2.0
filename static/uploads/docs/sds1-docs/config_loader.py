#!/usr/bin/env python3
"""
sds1 配置加载器
支持 YAML/JSON 配置加载、环境变量覆盖、热重载
"""

import os
import json
import yaml
import time
from pathlib import Path
from typing import Any, Optional, Dict

# 配置文件路径（相对于当前文件）
DEFAULT_CONFIG_PATH = Path(__file__).parent / "config.yaml"

# 环境变量前缀
ENV_PREFIX = "SDS_"


class ConfigLoader:
    """配置加载器，支持热重载和环境变量覆盖"""

    def __init__(self, config_path: Optional[str] = None):
        self._config_path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
        self._config: Dict[str, Any] = {}
        self._last_modified: float = 0
        self._last_check: float = 0
        self._check_interval: float = 1.0  # 检查间隔（秒）
        self._load()

    def _load(self) -> None:
        """加载配置文件"""
        if not self._config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {self._config_path}")

        with open(self._config_path, 'r', encoding='utf-8') as f:
            if self._config_path.suffix in ('.yaml', '.yml'):
                self._config = yaml.safe_load(f) or {}
            elif self._config_path.suffix == '.json':
                self._config = json.load(f)
            else:
                raise ValueError(f"不支持的配置文件格式: {self._config_path.suffix}")

        self._last_modified = self._config_path.stat().st_mtime
        self._last_check = time.time()

    def _check_reload(self) -> None:
        """检查文件是否修改，需要则重载"""
        now = time.time()
        if now - self._last_check < self._check_interval:
            return

        self._last_check = now
        try:
            current_mtime = self._config_path.stat().st_mtime
            if current_mtime > self._last_modified:
                self._load()
        except OSError:
            pass

    def _get_env_override(self, key_path: str) -> Optional[str]:
        """
        获取环境变量覆盖值
        key_path: 如 'paths.logs' -> 查找 SDS_PATHS_LOGS
        同时支持简写形式：如 'paths.logs' -> 查找 SDS_LOG_DIR
        """
        # 完整路径形式: SDS_PATHS_LOGS
        env_key = ENV_PREFIX + key_path.upper().replace('.', '_')
        if env_key in os.environ:
            return os.environ.get(env_key)
        
        # 简写形式: 对于 paths 下的键，支持 SDS_{KEY}_DIR
        # 例如 paths.logs -> SDS_LOGS_DIR, paths.output -> SDS_OUTPUT_DIR
        keys = key_path.split('.')
        if len(keys) == 2 and keys[0] == 'paths':
            short_key = ENV_PREFIX + keys[1].upper() + '_DIR'
            if short_key in os.environ:
                return os.environ.get(short_key)
        
        # 额外简写: paths.logs -> SDS_LOG_DIR (去掉复数s)
        if len(keys) == 2 and keys[0] == 'paths':
            singular_key = keys[1].rstrip('s').upper()
            alt_short_key = ENV_PREFIX + singular_key + '_DIR'
            if alt_short_key in os.environ:
                return os.environ.get(alt_short_key)
        
        return None

    def _get_nested(self, data: Dict, key_path: str) -> Any:
        """按点分隔路径获取嵌套值"""
        keys = key_path.split('.')
        current = data
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        return current

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值
        优先级：环境变量 > 配置文件 > 默认值

        Args:
            key: 配置键，支持点分隔路径，如 'paths.logs'
            default: 默认值

        Returns:
            配置值
        """
        self._check_reload()

        # 1. 检查环境变量覆盖
        env_value = self._get_env_override(key)
        if env_value is not None:
            # 尝试类型转换
            config_value = self._get_nested(self._config, key)
            if config_value is not None:
                try:
                    if isinstance(config_value, bool):
                        return env_value.lower() in ('true', '1', 'yes', 'on')
                    elif isinstance(config_value, int):
                        return int(env_value)
                    elif isinstance(config_value, float):
                        return float(env_value)
                    elif isinstance(config_value, list):
                        return env_value.split(',')
                except (ValueError, TypeError):
                    pass
            return env_value

        # 2. 从配置文件获取
        value = self._get_nested(self._config, key)
        if value is not None:
            return value

        # 3. 返回默认值
        return default

    def get_all(self) -> Dict[str, Any]:
        """获取完整配置（应用环境变量覆盖后）"""
        self._check_reload()
        result = self._deep_copy(self._config)
        self._apply_env_overrides(result)
        return result

    def _deep_copy(self, data: Any) -> Any:
        """深拷贝配置数据"""
        if isinstance(data, dict):
            return {k: self._deep_copy(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._deep_copy(item) for item in data]
        return data

    def _apply_env_overrides(self, data: Dict, prefix: str = "") -> None:
        """递归应用环境变量覆盖"""
        for key, value in data.items():
            current_path = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                self._apply_env_overrides(value, current_path)
            else:
                env_value = self._get_env_override(current_path)
                if env_value is not None:
                    try:
                        if isinstance(value, bool):
                            data[key] = env_value.lower() in ('true', '1', 'yes', 'on')
                        elif isinstance(value, int):
                            data[key] = int(env_value)
                        elif isinstance(value, float):
                            data[key] = float(env_value)
                        elif isinstance(value, list):
                            data[key] = env_value.split(',')
                        else:
                            data[key] = env_value
                    except (ValueError, TypeError):
                        data[key] = env_value

    def reload(self) -> None:
        """强制重新加载配置"""
        self._load()

    @property
    def config_path(self) -> Path:
        """获取配置文件路径"""
        return self._config_path

    @property
    def last_modified(self) -> float:
        """获取最后修改时间"""
        return self._last_modified


# 全局配置实例
_config_loader: Optional[ConfigLoader] = None


def get_config(key: str, default: Any = None) -> Any:
    """
    获取配置值的便捷函数

    Args:
        key: 配置键，支持点分隔路径，如 'paths.logs'
        default: 默认值

    Returns:
        配置值
    """
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader()
    return _config_loader.get(key, default)


def get_all_config() -> Dict[str, Any]:
    """获取完整配置的便捷函数"""
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader()
    return _config_loader.get_all()


def reload_config() -> None:
    """强制重新加载配置的便捷函数"""
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader()
    else:
        _config_loader.reload()


def init_config(config_path: Optional[str] = None) -> ConfigLoader:
    """
    初始化配置加载器（指定自定义路径）

    Args:
        config_path: 自定义配置文件路径

    Returns:
        ConfigLoader 实例
    """
    global _config_loader
    _config_loader = ConfigLoader(config_path)
    return _config_loader


# ============================================================
# 数据库密码特殊处理
# ============================================================

def get_db_password() -> Optional[str]:
    """获取数据库密码（优先从环境变量）"""
    return os.environ.get('SDS_DB_PASSWORD')


# ============================================================
# 主程序入口（测试用）
# ============================================================

if __name__ == "__main__":
    # print("=" * 60)
    # print("sds1 配置加载器测试")
    # print("=" * 60)

    # 测试1: 基本加载
    # print("\n[测试1] 基本配置加载")
    # print(f"配置文件路径: {get_config('')}")
    # print(f"日志路径: {get_config('paths.logs')}")
    # print(f"输出路径: {get_config('paths.output')}")
    # print(f"数据路径: {get_config('paths.data')}")

    # 测试2: 嵌套配置
    # print("\n[测试2] 嵌套配置读取")
    # print(f"主模型: {get_config('models.primary')}")
    # print(f"备用模型: {get_config('models.fallbacks')}")
    # print(f"分析间隔: {get_config('scheduling.analysis_interval')} 秒")
    # print(f"最小摘要长度: {get_config('thresholds.min_summary_length')} 字符")

    # 测试3: 数据库配置
    # print("\n[测试3] 数据库配置")
    # print(f"数据库主机: {get_config('database.host')}")
    # print(f"数据库端口: {get_config('database.port')}")
    # print(f"数据库用户: {get_config('database.user')}")
    # print(f"数据库名称: {get_config('database.database')}")
    db_password = get_db_password()
    # print(f"数据库密码: {'已设置' if db_password else '未设置（请设置 SDS_DB_PASSWORD 环境变量）'}")

    # 测试4: 完整配置
    # print("\n[测试4] 完整配置")
    all_config = get_all_config()
    # print(json.dumps(all_config, indent=2, ensure_ascii=False))

    # print("\n" + "=" * 60)
    # print("测试完成！")
    # print("=" * 60)
