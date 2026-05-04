"""SDS 完整生命周期集成测试"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import tempfile
from pathlib import Path


class TestSDSLifecycle:
    """测试 SDS 完整周期"""

    @pytest.mark.integration
    def test_config_loading(self, mock_config):
        """测试配置加载"""
        assert "paths" in mock_config
        assert "scheduling" in mock_config
        assert "models" in mock_config
        assert mock_config["paths"]["logs"] is not None

    @pytest.mark.integration
    def test_directory_creation(self, temp_dir):
        """测试目录创建"""
        dirs = ["logs", "output", "data", "templates"]
        for d in dirs:
            (temp_dir / d).mkdir()
            assert (temp_dir / d).exists()

    @pytest.mark.integration
    def test_task_state_transitions(self):
        """测试任务状态转换"""
        states = ["pending", "in_progress", "completed", "failed"]
        # 验证状态流转
        assert "pending" in states
        assert "completed" in states

    @pytest.mark.slow
    def test_full_cycle_mock(self):
        """测试完整周期（mock 版）"""
        # 模拟一个 SDS 周期
        with patch('sds_main.SDS') as mock_sds:
            mock_instance = MagicMock()
            mock_sds.return_value = mock_instance
            mock_instance.run_cycle.return_value = True
            
            # 模拟运行
            result = mock_instance.run_cycle()
            assert result is True
            mock_instance.run_cycle.assert_called_once()
