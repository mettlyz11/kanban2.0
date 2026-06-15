# alarm_channel_module

> 任务: v8 #20 可配置告警通道 — feishu/email/webhook
> 附件类型: 代码文件
> 生成时间: 2026-05-12 06:56

# 告警通道核心实现

本模块提供可配置告警通道的核心功能，支持飞书、邮件、Webhook三种通道，包括数据模型、通道策略、模板引擎和路由决策。

## 目录结构

```
alarm_channel/
├── __init__.py
├── models.py
├── config.py
├── template_engine.py
├── app.py
└── channels/
    ├── __init__.py
    ├── base.py
    ├── feishu.py
    ├── email.py
    └── webhook.py
```

---

### `alarm_channel/__init__.py`

```python
"""告警通道模块初始化与导出"""
from .config import ConfigLoader
from .template_engine import TemplateEngine
from .channels.base import BaseChannel
from .channels.feishu import FeishuChannel
from .channels.email import EmailChannel
from .channels.webhook import WebhookChannel

__all__ = [
    'ConfigLoader',
    'TemplateEngine',
    'BaseChannel',
    'FeishuChannel',
    'EmailChannel',
    'WebhookChannel'
]
```

---

### `alarm_channel/models.py`

```python
"""告警消息数据模型"""
import json
from datetime import datetime
from typing import List, Optional, Dict, Any

class AlertStatus:
    FIRING = "firing"
    RESOLVED = "resolved"

class Alert:
    """单个告警对象"""
    def __init__(self, status: str, labels: Dict[str, str], annotations: Dict[str, str],
                 starts_at: str, ends_at: str = "", generator_url: str = ""):
        self.status = status
        self.labels = labels
        self.annotations = annotations
        self.starts_at = starts_at
        self.ends_at = ends_at
        self.generator_url = generator_url

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "labels": self.labels,
            "annotations": self.annotations,
            "startsAt": self.starts_at,
            "endsAt": self.ends_at,
            "generatorURL": self.generator_url
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Alert':
        return cls(
            status=data.get("status", AlertStatus.FIRING),
            labels=data.get("labels", {}),
            annotations=data.get("annotations", {}),
            starts_at=data.get("startsAt", ""),
            ends_at=data.get("endsAt", ""),
            generator_url=data.get("generatorURL", "")
        )

class AlertManagerPayload:
    """AlertManager Webhook 请求体"""
    def __init__(self, version: str, group_key: str, status: str, receiver: str,
                 group_labels: Dict[str, str], common_labels: Dict[str, str],
                 common_annotations: Dict[str, str], external_url: str,
                 alerts: List[Alert]):
        self.version = version
        self.group_key = group_key
        self.status = status
        self.receiver = receiver
        self.group_labels = group_labels
        self.common_labels = common_labels
        self.common_annotations = common_annotations
        self.external_url = external_url
        self.alerts = alerts

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "groupKey": self.group_key,
            "status": self.status,
            "receiver": self.receiver,
            "groupLabels": self.group_labels,
            "commonLabels": self.common_labels,
            "commonAnnotations": self.common_annotations,
            "externalURL": self.external_url,
            "alerts": [a.to_dict() for a in self.alerts]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AlertManagerPayload':
        alerts = [Alert.from_dict(a) for a in data.get("alerts", [])]
        return cls(
            version=data.get("version", ""),
            group_key=data.get("groupKey", ""),
            status=data.get("status", "firing"),
            receiver=data.get("receiver", ""),
            group_labels=data.get("groupLabels", {}),
            common_labels=data.get("commonLabels", {}),
            common_annotations=data.get("commonAnnotations", {}),
            external_url=data.get("externalURL", ""),
            alerts=alerts
        )
```

---

### `alarm_channel/channels/base.py`

```python
"""通道策略基类接口"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class BaseChannel(ABC):
    """所有告警通道的基类，定义发送接口"""

    def __init__(self, config: Dict[str, Any]):
        """
        :param config: 通道配置字典，包含通道所需的参数（如URL、认证信息等）
        """
        self.config = config

    @abstractmethod
    def send(self, message: Dict[str, Any]) -> bool:
        """
        发送告警消息
        :param message: 渲染后的消息内容（字典或字符串形式）
        :return: 发送成功返回 True，否则 False
        """
        pass

    @abstractmethod
    def validate_config(self) -> bool:
        """验证通道配置是否有效"""
        pass

    def __repr__(self):
        return f"{self.__class__.__name__}(config={self.config.get('name','')})"
```

---

### `alarm_channel/channels/__init__.py`

```python
from .base import BaseChannel
from .feishu import FeishuChannel
from .email import EmailChannel
from .webhook import WebhookChannel

__all__ = ['BaseChannel', 'FeishuChannel', 'EmailChannel', 'WebhookChannel']
```

---

### `alarm_channel/channels/feishu.py`

```python
"""飞书通道实现"""
import json
import logging
from typing import Dict, Any

import requests

from .base import BaseChannel

logger = logging.getLogger(__name__)

class FeishuChannel(BaseChannel):
    """通过飞书机器人 Webhook 发送告警消息"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.webhook_url = config.get("webhook_url", "")
        self.secret = config.get("secret", "")  # 可选，用于签名验证
        self.send_type = config.get("send_type", "interactive")  # interactive 或 text

    def validate_config(self) -> bool:
        if not self.webhook_url:
            logger.error("飞书通道配置缺少 webhook_url")
            return False
        return True

    def _build_sign(self, timestamp: int) -> str:
        """生成签名（飞书机器人安全设置）"""
        import hashlib
        import base64
        import hmac

        string_to_sign = f"{timestamp}\n{self.secret}"
        hmac_code = hmac.new(
            string_to_sign.encode("utf-8"),
            digestmod=hashlib.sha256
        )
        sign = base64.b64encode(hmac_code.digest())
        return sign.decode("utf-8")

    def _build_payload(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """根据 send_type 构建飞书消息体"""
        if self.send_type == "text":
            content = message.get("text", "")
            return {
                "msg_type": "text",
                "content": {"text": content}
            }
        else:
            # interactive 卡片格式
            card = message.get("card", message)
            payload = {
                "msg_type": "interactive",
                "card": card
            }
            return payload

    def send(self, message: Dict[str, Any]) -> bool:
        if not self.validate_config():
            return False

        payload = self._build_payload(message)
        headers = {"Content-Type": "application/json"}
        timestamp = int(datetime.now().timestamp()) if self.secret else None
        if timestamp:
            sign = self._build_sign(timestamp)
            payload["timestamp"] = str(timestamp)
            payload["sign"] = sign

        try:
            resp = requests.post(
                self.webhook_url,
                data=json.dumps(payload),
                headers=headers,
                timeout=10
            )
            if resp.status_code == 200:
                result = resp.json()
                if result.get("code") == 0:
                    logger.info(f"飞书消息发送成功: {self.webhook_url[-20:]}")
                    return True
                else:
                    logger.error(f"飞书返回错误: {result.get('msg')}")
            else:
                logger.error(f"飞书请求失败, HTTP {resp.status_code}: {resp.text}")
        except requests.RequestException as e:
            logger.exception(f"飞书消息发送异常: {e}")
        return False

# 修复导入
from datetime import datetime
```

---

### `alarm_channel/channels/email.py`

```python
"""邮件通道实现"""
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from typing import Dict, Any, List

from .base import BaseChannel

logger = logging.getLogger(__name__)

class EmailChannel(BaseChannel):
    """通过 SMTP 发送告警邮件"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.smtp_host = config.get("smtp_host", "")
        self.smtp_port = config.get("smtp_port", 465)
        self.smtp_ssl = config.get("smtp_ssl", True)
        self.username = config.get("username", "")
        self.password = config.get("password", "")
        self.from_addr = config.get("from_addr", self.username)
        self.to_addrs = config.get("to_addrs", [])
        self.cc_addrs = config.get("cc_addrs", [])

    def validate_config(self) -> bool:
        if not self.smtp_host or not self.from_addr or not self.to_addrs:
            logger.error("邮件通道配置不完整（缺少 smtp_host/from_addr/to_addrs）")
            return False
        return True

    def send(self, message: Dict[str, Any]) -> bool:
        if not self.validate_config():
            return False

        subject = message.get("subject", "告警通知")
        body_html = message.get("body_html", "")
        body_text = message.get("body_text", "")

        msg = MIMEMultipart('alternative')
        msg['Subject'] = Header(subject, 'utf-8')
        msg['From'] = self.from_addr
        msg['To'] = ', '.join(self.to_addrs)
        if self.cc_addrs:
            msg['Cc'] = ', '.join(self.cc_addrs)

        # 添加纯文本和HTML版本
        if body_text:
            part_text = MIMEText(body_text, 'plain', 'utf-8')
            msg.attach(part_text)
        if body_html:
            part_html = MIMEText(body_html, 'html', 'utf-8')
            msg.attach(part_html)

        # 连接SMTP服务器
        try:
            if self.smtp_ssl:
                server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, timeout=10)
            else:
                server = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10)
                server.starttls()

            if self.username and self.password:
                server.login(self.username, self.password)

            # 收件人列表（包含CC）
            all_recipients = self.to_addrs + self.cc_addrs
            server.sendmail(self.from_addr, all_recipients, msg.as_string())
            server.quit()
            logger.info(f"邮件发送成功 to {all_recipients}")
            return True
        except (smtplib.SMTPException, ConnectionError) as e:
            logger.exception(f"邮件发送失败: {e}")
            return False
```

---

### `alarm_channel/channels/webhook.py`

```python
"""通用 Webhook 通道实现"""
import json
import logging
from typing import Dict, Any

import requests

from .base import BaseChannel

logger = logging.getLogger(__name__)

class WebhookChannel(BaseChannel):
    """通过 HTTP POST 发送告警消息到任意 Webhook 地址"""

    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.url = config.get("url", "")
        self.method = config.get("method", "POST").upper()
        self.headers = config.get("headers", {"Content-Type": "application/json"})
        self.timeout = config.get("timeout", 15)

    def validate_config(self) -> bool:
        if not self.url:
            logger.error("Webhook 通道配置缺少 url")
            return False
        return True

    def send(self, message: Dict[str, Any]) -> bool:
        if not self.validate_config():
            return False

        # 将 message 转为 JSON 或原样发送
        if isinstance(message, dict):
            data = json.dumps(message, ensure_ascii=False).encode('utf-8')
        else:
            data = message

        try:
            if self.method == "POST":
                resp = requests.post(
                    self.url,
                    data=data,
                    headers=self.headers,
                    timeout=self.timeout
                )
            elif self.method == "PUT":
                resp = requests.put(
                    self.url,
                    data=data,
                    headers=self.headers,
                    timeout=self.timeout
                )
            else:
                logger.error(f"不支持的 HTTP 方法: {self.method}")
                return False

            if 200 <= resp.status_code < 300:
                logger.info(f"Webhook 发送成功: {self.url}")
                return True
            else:
                logger.error(f"Webhook 返回异常状态码: {resp.status_code}, 响应: {resp.text[:200]}")
                return False
        except requests.RequestException as e:
            logger.exception(f"Webhook 请求异常: {e}")
            return False
```

---

### `alarm_channel/template_engine.py`

```python
"""模板渲染引擎（支持 Jinja2 和简单字符串替换）"""
import re
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

try:
    from jinja2 import Environment, FileSystemLoader, BaseLoader
    HAS_JINJA = True
except ImportError:
    HAS_JINJA = False


class TemplateEngine:
    """模板引擎，用于渲染告警消息内容"""

    def __init__(self, template_dir: Optional[str] = None, cache_enabled: bool = True):
        """
        :param template_dir: 模板文件目录（可选），如果提供则使用文件模板
        :param cache_enabled: 是否启用 Jinja2 缓存（仅当模板目录存在时有效）
        """
        self.template_dir = template_dir
        self.cache_enabled = cache_enabled
        self.env = None

        if template_dir and HAS_JINJA:
            self.env = Environment(
                loader=FileSystemLoader(template_dir),
                auto_reload=not cache_enabled,
                enable_async=False
            )
        elif HAS_JINJA:
            # 使用内存加载器，支持字符串模板
            from jinja2 import BaseLoader, TemplateNotFound
            class StringLoader(BaseLoader):
                def __init__(self, templates: Dict[str, str]):
                    self.templates = templates
                def get_source(self, environment, template):
                    if template in self.templates:
                        return self.templates[template], template, lambda: True
                    raise TemplateNotFound(template)
            self.env = Environment(loader=StringLoader({}), autoescape=True)

    def render_string(self, template_str: str, variables: Dict[str, Any]) -> str:
        """使用字符串模板渲染"""
        try:
            if self.env:
                # 使用 Jinja2
                from jinja2 import Template
                t = Template(template_str)
                return t.render(**variables)
            else:
                # 使用简单的 {{ key }} 替换
                return self._simple_render(template_str, variables)
        except Exception as e:
            logger.exception(f"模板渲染失败: {e}")
            return template_str  # fallback to original