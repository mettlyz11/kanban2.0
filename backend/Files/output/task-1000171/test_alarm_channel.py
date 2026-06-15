# test_alarm_channel

> 任务: v8 #20 可配置告警通道 — feishu/email/webhook
> 附件类型: 测试代码
> 生成时间: 2026-05-12 06:57

# 可配置告警通道测试代码

## 概述
本测试套件用于验证告警通道模块（飞书、Email、Webhook）的各组件在隔离环境下的正确性，包括数据模型序列化、通道发送、模板引擎、配置加载以及端到端集成。测试基于 `pytest` 和 `unittest.mock`，所有外部 HTTP/SMTP 请求均被 Mock，确保可离线执行。

---

## 1. `test_models.py` — 数据模型序列化与反序列化

```python
import pytest
from datetime import datetime
from pydantic import ValidationError
from alerting.models import (
    Alert,
    AlertSeverity,
    ChannelType,
    ChannelConfig,
    RoutingRule,
    AlertManagerWebhook,
)

class TestAlertModel:
    """告警数据模型的序列化与反序列化"""

    def test_alert_minimal(self):
        """最小必填字段构造"""
        alert = Alert(
            title="CPU usage > 90%",
            severity=AlertSeverity.WARNING,
            source="prometheus",
        )
        assert alert.title == "CPU usage > 90%"
        assert alert.severity == AlertSeverity.WARNING
        assert alert.source == "prometheus"
        assert alert.labels == {}
        assert alert.annotations == {}
        assert isinstance alert.starts_at, datetime

    def test_alert_full(self):
        """完整字段构造与 JSON 序列化"""
        alert = Alert(
            title="Disk full on /data",
            severity=AlertSeverity.CRITICAL,
            source="node_exporter",
            labels={"instance": "db-01", "mountpoint": "/data"},
            annotations={"summary": "Disk usage 98%", "runbook": "https://runbook.example.com/disk-full"},
            starts_at=datetime(2025, 3, 1, 12, 0, 0),
        )
        json_str = alert.model_dump_json()
        recovered = Alert.model_validate_json(json_str)
        assert recovered == alert
        assert recovered.labels["mountpoint"] == "/data"

    def test_alert_invalid_severity(self):
        """非法的严重级别应触发验证错误"""
        with pytest.raises(ValidationError):
            Alert(
                title="test",
                severity="UNKNOWN",  # 不在 AlertSeverity 枚举中
                source="test",
            )

    def test_channel_config_feishu(self):
        """飞书通道配置序列化"""
        config = ChannelConfig(
            type=ChannelType.FEISHU,
            feishu_webhook_url="https://open.feishu.cn/open-apis/bot/v2/hook/xxxxx",
            feishu_secret="mysecret",
        )
        data = config.model_dump()
        assert data["type"] == "feishu"
        assert "feishu_webhook_url" in data
        recovered = ChannelConfig(**data)
        assert recovered.feishu_secret.get_secret_value() == "mysecret"

    def test_channel_config_email(self):
        """邮件通道配置序列化"""
        config = ChannelConfig(
            type=ChannelType.EMAIL,
            email_smtp_host="smtp.example.com",
            email_smtp_port=587,
            email_username="alert@example.com",
            email_password="smtp_password",
            email_from="alert@example.com",
            email_to=["ops@example.com"],
        )
        json_str = config.model_dump_json()
        recovered = ChannelConfig.model_validate_json(json_str)
        assert recovered.email_smtp_host == "smtp.example.com"
        assert recovered.email_to == ["ops@example.com"]

    def test_routing_rule_match_severity(self):
        """路由规则：按严重程度匹配"""
        rule = RoutingRule(
            name="critical to email",
            match_severity=[AlertSeverity.CRITICAL],
            channel_configs=["email-critical"],
        )
        alert = Alert(title="test", severity=AlertSeverity.CRITICAL, source="test")
        assert rule.matches(alert) is True

        alert2 = Alert(title="test2", severity=AlertSeverity.WARNING, source="test")
        assert rule.matches(alert2) is False

    def test_routing_rule_match_labels(self):
        """路由规则：按标签匹配"""
        rule = RoutingRule(
            name="instance match",
            match_labels={"instance": "db-*"},
            channel_configs=["email-db"],
        )
        alert = Alert(title="db down", severity=AlertSeverity.CRITICAL, source="test", labels={"instance": "db-01"})
        assert rule.matches(alert) is True

        alert2 = Alert(title="web down", severity=AlertSeverity.CRITICAL, source="test", labels={"instance": "web-01"})
        assert rule.matches(alert2) is False

    def test_alertmanager_webhook(self):
        """解析 AlertManager Webhook payload"""
        payload = {
            "version": "4",
            "groupKey": "{}:{alertname=\"HighMemoryUsage\"}",
            "status": "firing",
            "receiver": "default",
            "groupLabels": {"alertname": "HighMemoryUsage"},
            "commonLabels": {"severity": "critical", "team": "ops"},
            "commonAnnotations": {"summary": "Memory > 90%"},
            "alerts": [
                {
                    "status": "firing",
                    "labels": {"alertname": "HighMemoryUsage", "instance": "web-01"},
                    "annotations": {"summary": "Memory on web-01 > 90%"},
                    "startsAt": "2025-03-01T14:00:00Z",
                    "endsAt": "0001-01-01T00:00:00Z",
                    "generatorURL": "http://alertmanager:9093/...",
                }
            ],
        }
        webhook = AlertManagerWebhook.model_validate(payload)
        assert len(webhook.alerts) == 1
        alert = webhook.alerts[0]
        assert alert.severity == AlertSeverity.CRITICAL
        assert alert.labels["instance"] == "web-01"
```

---

## 2. `test_channels_feishu.py` — 飞书通道发送测试

```python
import pytest
from unittest.mock import Mock, patch, call
from alerting.channels.feishu import FeishuChannel
from alerting.models import Alert, ChannelConfig, ChannelType, AlertSeverity

class TestFeishuChannel:
    """飞书通道发送测试（mock HTTP POST）"""

    @patch("alerting.channels.feishu.requests.post")
    def test_send_text_message(self, mock_post):
        """发送文本消息"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"StatusCode": 0, "StatusMessage": "success"}
        mock_post.return_value = mock_response

        config = ChannelConfig(
            type=ChannelType.FEISHU,
            feishu_webhook_url="https://open.feishu.cn/open-apis/bot/v2/hook/testhook",
            feishu_secret="",
        )
        channel = FeishuChannel(config)
        alert = Alert(
            title="Test Alert",
            severity=AlertSeverity.WARNING,
            source="test",
            annotations={"summary": "Just a test"},
        )
        result = channel.send(alert)
        assert result.success is True
        # 验证POST调用
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == config.feishu_webhook_url
        payload = call_args[1]["json"]
        assert "text" in payload["content"]

    @patch("alerting.channels.feishu.requests.post")
    def test_send_with_signature(self, mock_post):
        """带签名的飞书消息"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"StatusCode": 0}
        mock_post.return_value = mock_response

        config = ChannelConfig(
            type=ChannelType.FEISHU,
            feishu_webhook_url="https://open.feishu.cn/open-apis/bot/v2/hook/signed",
            feishu_secret="my_secret_key",
        )
        channel = FeishuChannel(config)
        alert = Alert(
            title="Signed",
            severity=AlertSeverity.CRITICAL,
            source="test",
        )
        result = channel.send(alert)
        assert result.success is True
        payload = mock_post.call_args[1]["json"]
        assert "timestamp" in payload
        assert "sign" in payload

    @patch("alerting.channels.feishu.requests.post")
    def test_send_failure(self, mock_post):
        """发送失败场景"""
        mock_response = Mock()
        mock_response.status_code = 403
        mock_post.return_value = mock_response

        config = ChannelConfig(type=ChannelType.FEISHU, feishu_webhook_url="http://invalid")
        channel = FeishuChannel(config)
        alert = Alert(title="Fail", severity=AlertSeverity.WARNING, source="test")
        result = channel.send(alert)
        assert result.success is False
        assert "403" in result.error_message

    @patch("alerting.channels.feishu.requests.post")
    def test_network_timeout(self, mock_post):
        """网络超时处理"""
        from requests.exceptions import Timeout
        mock_post.side_effect = Timeout("Connection timed out")

        config = ChannelConfig(
            type=ChannelType.FEISHU,
            feishu_webhook_url="https://open.feishu.cn/bot/timeout",
        )
        channel = FeishuChannel(config)
        alert = Alert(title="Timeout test", severity=AlertSeverity.WARNING, source="test")
        result = channel.send(alert)
        assert result.success is False
        assert "Timeout" in result.error_message
```

---

## 3. `test_channels_email.py` — 邮件通道发送测试

```python
import pytest
from unittest.mock import Mock, patch, MagicMock
from alerting.channels.email import EmailChannel
from alerting.models import Alert, ChannelConfig, ChannelType, AlertSeverity

class TestEmailChannel:
    """邮件通道发送测试（mock SMTP）"""

    @patch("alerting.channels.email.smtplib.SMTP")
    def test_send_html_email(self, mock_smtp):
        """发送HTML格式邮件"""
        # 模拟 SMTP 实例
        mock_smtp_instance = MagicMock()
        mock_smtp.return_value = mock_smtp_instance

        config = ChannelConfig(
            type=ChannelType.EMAIL,
            email_smtp_host="smtp.example.com",
            email_smtp_port=587,
            email_username="alert@example.com",
            email_password="secret",
            email_from="alert@example.com",
            email_to=["ops@example.com"],
        )
        channel = EmailChannel(config)
        alert = Alert(
            title="Disk Warning",
            severity=AlertSeverity.WARNING,
            source="test",
            annotations={"summary": "Disk usage 85%"},
            labels={"instance": "server01"},
        )
        result = channel.send(alert)
        assert result.success is True
        # 验证SMTP调用
        mock_smtp.assert_called_once_with("smtp.example.com", 587)
        mock_smtp_instance.starttls.assert_called_once()
        mock_smtp_instance.login.assert_called_once_with("alert@example.com", "secret")
        # 检查发送内容
        send_message_call = mock_smtp_instance.send_message
        assert send_message_call.called
        msg = send_message_call.call_args[0][0]
        assert "Disk Warning" in msg["Subject"]
        assert msg["From"] == "alert@example.com"
        assert msg["To"] == "ops@example.com"
        assert msg.get_content_type() == "text/html"

    @patch("alerting.channels.email.smtplib.SMTP")
    def test_smtp_authentication_failure(self, mock_smtp):
        """SMTP认证失败"""
        import smtplib
        mock_smtp_instance = MagicMock()
        mock_smtp_instance.login.side_effect = smtplib.SMTPAuthenticationError(535, b"Authentication failed")
        mock_smtp.return_value = mock_smtp_instance

        config = ChannelConfig(
            type=ChannelType.EMAIL,
            email_smtp_host="smtp.example.com",
            email_smtp_port=587,
            email_username="wrong",
            email_password="wrong",
            email_from="alert@example.com",
            email_to=["ops@example.com"],
        )
        channel = EmailChannel(config)
        alert = Alert(title="Test", severity=AlertSeverity.WARNING, source="test")
        result = channel.send(alert)
        assert result.success is False
        assert "Authentication failed" in result.error_message

    @patch("alerting.channels.email.smtplib.SMTP")
    def test_multiple_recipients(self, mock_smtp):
        """多个收件人"""
        mock_smtp_instance = MagicMock()
        mock_smtp.return_value = mock_smtp_instance

        config = ChannelConfig(
            type=ChannelType.EMAIL,
            email_smtp_host="smtp.example.com",
            email_smtp_port=587,
            email_username="alert@example.com",
            email_password="secret",
            email_from="alert@example.com",
            email_to=["ops@example.com", "oncall@example.com"],
        )
        channel = EmailChannel(config)
        alert = Alert(title="Multi", severity=AlertSeverity.CRITICAL, source="test")
        result = channel.send(alert)
        assert result.success is True
        msg = mock_smtp_instance.send_message.call_args[0][0]
        assert msg["To"] == "ops@example.com, oncall@example.com"
```

---

## 4. `test_channels_webhook.py` — Webhook通道发送测试

```python
import pytest
from unittest.mock import Mock, patch
from alerting.channels.webhook import WebhookChannel
from alerting.models import Alert, ChannelConfig, ChannelType, AlertSeverity

class TestWebhookChannel:
    """Webhook通道发送测试（mock HTTP POST）"""

    @patch("alerting.channels.webhook.requests.post")
    def test_send_json_payload(self, mock_post):
        """发送标准JSON payload"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "OK"
        mock_post.return_value = mock_response

        config = ChannelConfig(
            type=ChannelType.WEBHOOK,
            webhook_url="https://hooks.example.com/alerts",
            webhook_headers={"Authorization": "Bearer token123"},
        )
        channel = WebhookChannel(config)
        alert = Alert(
            title="CPU Overload",
            severity=AlertSeverity.CRITICAL,
            source="prometheus",
            labels={"cpu": "core0"},
        )
        result = channel.send(alert)
        assert result.success is True
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args[1]
        assert call_kwargs["url"] == config.webhook_url
        assert call_kwargs["headers"]["Authorization"] == "Bearer token123"
        payload = call_kwargs["json"]
        assert payload["title"] == "CPU Overload"
        assert payload["severity"] == "critical"
        assert payload["labels"]["cpu"] == "core0"

    @patch("alerting.channels.webhook.requests.post")
    def test_custom_payload_format(self, mock_post):
        """自定义payload格式（通过模板）"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        config = ChannelConfig(
            type=ChannelType.WEBHOOK,
            webhook_url="https://custom.example.com/alert",
            webhook_template="""{
                "msg": "{{ alert.title }}",
                "level": "{{ alert.severity }}",
                "instance": "{{ alert.labels.get('instance', 'unknown') }}"
            }""",
        )
        channel = WebhookChannel(config)
        alert = Alert(
            title="Disk Full",
            severity=AlertSeverity.WARNING,
            source="test",
            labels={"instance": "db-02"},
        )
        result = channel.send(alert)
        assert result.success is True
        payload = mock_post.call_args[1]["json"]
        assert payload["msg"] == "Disk Full"
        assert payload["level"] == "warning"
        assert payload["instance"] == "db-02"

    @patch("alerting.channels.webhook.requests.post")
    def test_http_error(self, mock_post):
        """HTTP非200响应"""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        mock_post.return_value = mock_response

        config = ChannelConfig(
            type=ChannelType.WEBHOOK,
            web