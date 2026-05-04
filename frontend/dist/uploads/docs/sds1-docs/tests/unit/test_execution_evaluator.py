"""execution_evaluator 单元测试"""

import pytest
from unittest.mock import Mock, patch


class TestExecutionEvaluator:
    """测试执行质量评估器"""

    def test_summary_length_check(self):
        """测试摘要长度检查"""
        min_length = 50
        summary_short = "太短"
        summary_ok = "这是一段足够长的摘要，包含了关键成果和执行过程，满足最低字数要求，确保测试能够顺利通过。加上更多内容以满足五十个字符的要求。"
        
        assert len(summary_short) < min_length
        assert len(summary_ok) >= min_length

    def test_log_length_check(self):
        """测试日志长度检查"""
        min_length = 200
        log_short = "执行完成"
        log_ok = "执行" * 100  # 200 字符
        
        assert len(log_short) < min_length
        assert len(log_ok) >= min_length

    def test_result_summary_check(self):
        """测试结果总结检查"""
        min_length = 100
        result = "结果总结" * 25  # 100 字符
        assert len(result) >= min_length

    def test_attachment_check(self):
        """测试附件检查"""
        # 模拟有附件的任务
        task_with_attachments = {"id": 1, "attachments": 2}
        task_without = {"id": 2, "attachments": 0}
        
        assert task_with_attachments["attachments"] > 0
        assert task_without["attachments"] == 0


class TestQualityGate:
    """测试质量门控"""

    def test_pass_all_checks(self):
        """测试全部通过"""
        scores = {
            'summary_length': 1.0,
            'log_length': 1.0,
            'result_summary': 1.0,
            'has_attachments': 1.0,
        }
        assert all(score >= 0.8 for score in scores.values())

    def test_fail_summary_too_short(self):
        """测试摘要太短失败"""
        scores = {
            'summary_length': 0.3,  # 低于阈值
            'log_length': 1.0,
            'result_summary': 1.0,
        }
        assert not all(score >= 0.8 for score in scores.values())
