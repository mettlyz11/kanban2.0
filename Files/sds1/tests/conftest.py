"""pytest 共享配置和 fixtures"""

import pytest
import tempfile
import os
from pathlib import Path

@pytest.fixture
def temp_dir():
    """创建临时目录"""
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp)

@pytest.fixture
def mock_config(temp_dir):
    """提供测试用的配置字典"""
    return {
        "paths": {
            "logs": str(temp_dir / "logs"),
            "output": str(temp_dir / "output"),
            "data": str(temp_dir / "data"),
            "templates": str(temp_dir / "templates"),
            "backups": str(temp_dir / "backups"),
            "reports": str(temp_dir / "reports"),
        },
        "scheduling": {
            "analysis_interval": 60,
            "generation_interval": 120,
            "scheduler_interval": 30,
            "max_retry_attempts": 2,
            "retry_delay": 1,
        },
        "models": {
            "primary": "test-model",
            "fallbacks": ["fallback-1", "fallback-2"],
            "timeout": 10,
            "max_tokens": 1000,
            "temperature": 0.5,
        },
        "thresholds": {
            "min_summary_length": 10,
            "min_log_length": 5,
            "max_summary_length": 500,
            "min_confidence_score": 0.5,
            "max_processing_time": 30,
        },
        "database": {
            "host": "localhost",
            "port": 3306,
            "user": "test_user",
            "database": "test_db",
            "pool_size": 2,
            "max_overflow": 5,
            "pool_timeout": 10,
        },
    }

@pytest.fixture
def clean_env():
    """清理 SDS 环境变量"""
    old_env = {}
    for key in list(os.environ.keys()):
        if key.startswith("SDS_"):
            old_env[key] = os.environ.pop(key)
    yield
    for key, value in old_env.items():
        os.environ[key] = value
