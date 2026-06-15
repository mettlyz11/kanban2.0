# api_documentation

> 任务: v8 #20 可配置告警通道 — feishu/email/webhook
> 附件类型: API文档
> 生成时间: 2026-05-12 06:58

# v8 #20 可配置告警通道 — API 文档

**版本**: 1.0.0  
**更新日期**: 2025-04-10  
**作者**: 告警通道团队  
**状态**: 正式发布  

---

## 1. 概述

本文档定义了可配置告警通道模块的对外 API 接口，包括：

- **Webhook 接收接口**：用于接收外部系统推送的告警事件，并将其路由到已配置的通道（飞书、邮件、自定义 Webhook）。
- **通道策略接口**：提供通道基类与扩展规范，允许开发者自定义新的告警通道。
- **模板引擎接口**：用于将告警数据渲染为特定格式的消息（如飞书卡片、邮件正文）。
- **配置加载器**：定义配置文件的加载方式与返回结构。
- **健康检查接口**：用于监控模块运行状态。

所有接口均采用 RESTful 风格，请求/响应数据格式默认为 JSON（API 接口）或 YAML（配置文件）。本文档适用于后端开发人员、运维人员以及希望集成自定义告警通道的第三方开发者。

---

## 2. Webhook 接收接口

### 2.1 POST /alerts

接收外部系统（如 Prometheus、Zabbix 等）推送的告警事件。系统将根据告警的元数据匹配已配置的通道策略，并调用对应通道发送通知。

#### 2.1.1 请求格式

**HTTP 方法**: POST  
**Content-Type**: `application/json`  
**URL**: `https://your-alert-host/api/v1/alerts`

**请求体结构**:

| 字段 | 类型 | 必填 | 描述 |
|------|------|------|------|
| `name` | string | 是 | 告警名称，用于标识告警规则 |
| `status` | string | 是 | 告警状态：`firing` (触发) 或 `resolved` (恢复) |
| `severity` | string | 是 | 严重级别：`critical`, `warning`, `info` |
| `labels` | object | 否 | 标签，如 `{"env": "prod", "service": "api"}` |
| `annotations` | object | 否 | 注解，如 `{"summary": "CPU 使用率过高", "description": "当前使用率 95%", "runbook": "http://runbook"}` |
| `startsAt` | string | 是 | ISO8601 格式的开始时间，如 `"2025-04-10T10:00:00Z"` |
| `endsAt` | string | 否 | 结束时间，恢复时需提供 |
| `generatorURL` | string | 否 | 告警生成器的 URL |

**请求示例**:

```json
{
  "name": "HighCPUUsage",
  "status": "firing",
  "severity": "critical",
  "labels": {
    "env": "prod",
    "service": "api-gateway"
  },
  "annotations": {
    "summary": "CPU 使用率超过 90%",
    "description": "Service api-gateway CPU 当前使用率为 95%",
    "runbook": "https://wiki/runbooks/cpu"
  },
  "startsAt": "2025-04-10T10:05:00Z",
  "endsAt": "",
  "generatorURL": "https://prometheus.example.com/graph?g0.expr=cpu_usage"
}
```

#### 2.1.2 响应格式

**HTTP 状态码**:  
- `200 OK`: 成功接收并处理（至少一个通道发送成功）
- `202 Accepted`: 已接收，异步处理（队列模式下）
- `400 Bad Request`: 请求格式错误
- `500 Internal Server Error`: 处理失败

**响应体结构**:

| 字段 | 类型 | 描述 |
|------|------|------|
| `code` | int | 状态码，`200` 表示成功 |
| `message` | string | 处理结果描述 |
| `alert_id` | string | 唯一告警 ID（UUID），用于后续查询 |
| `channels` | array | 本次触发的通道列表及其状态 |

**响应示例**:

```json
{
  "code": 200,
  "message": "Alert processed successfully",
  "alert_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "channels": [
    {
      "channel_type": "feishu",
      "status": "sent",
      "target": "group1"
    },
    {
      "channel_type": "email",
      "status": "sent",
      "target": "ops@example.com"
    }
  ]
}
```

#### 2.1.3 错误码

| HTTP 状态码 | code | message | 说明 |
|-------------|------|---------|------|
| 400 | 40001 | Invalid request body | 请求 JSON 解析失败 |
| 400 | 40002 | Missing required field: name | 缺少必填字段 |
| 400 | 40003 | Invalid status value: ... | 状态值只能为 firing/resolved |
| 500 | 50001 | Internal processing error | 内部错误，如通道配置读取失败 |

---

## 3. 通道策略接口

所有告警通道必须实现基类 `BaseChannel`，并遵循统一规范。系统通过工厂模式根据配置中的 `type` 字段实例化对应通道。

### 3.1 基类定义

**通道基类 `BaseChannel`**（Python 代码示例）:

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class AlertData:
    """告警数据包装类"""
    def __init__(self, raw: Dict[str, Any]):
        self.name = raw.get("name", "")
        self.status = raw.get("status", "firing")
        self.severity = raw.get("severity", "info")
        self.labels = raw.get("labels", {})
        self.annotations = raw.get("annotations", {})
        self.starts_at = raw.get("startsAt", "")
        self.ends_at = raw.get("endsAt", "")
        self.generator_url = raw.get("generatorURL", "")
        self.alert_id = raw.get("alert_id", "")  # 由系统生成后注入

class BaseChannel(ABC):
    """通道基类，所有通道必须继承此类"""

    def __init__(self, config: Dict[str, Any]):
        """
        初始化通道实例
        :param config: 通道专属配置，如 webhook URL、邮箱地址等
        """
        self.config = config
        self.name = config.get("name", "unnamed")
        self.type = config.get("type", "unknown")

    @abstractmethod
    async def send(self, alert: AlertData) -> Dict[str, Any]:
        """
        发送告警到目标通道
        :param alert: 告警数据对象
        :return: 字典，必须包含 'status' 字段（'sent' 或 'failed'），
                 可选 'error' 字段描述失败原因
                 可选 'target' 字段指明发送目标
        """
        pass

    @abstractmethod
    def validate_config(self) -> bool:
        """
        验证通道配置是否合法
        :return: True 合法，False 不合法
        """
        pass
```

### 3.2 自定义通道实现规范

开发者需要：

1. 继承 `BaseChannel`。
2. 实现 `send` 和 `validate_config` 方法。
3. 在配置中指定 `type` 为自定义通道的唯一标识（如 `"my_webhook"`）。
4. 注册通道类到通道工厂（可通过装饰器或配置文件映射）。

**示例：实现飞书通道**

```python
import json
import aiohttp
from your_alert_system.channels import BaseChannel, AlertData

class FeishuChannel(BaseChannel):
    """飞书群机器人通道"""

    async def send(self, alert: AlertData) -> Dict[str, Any]:
        webhook_url = self.config.get("webhook_url", "")
        if not webhook_url:
            return {"status": "failed", "error": "missing webhook_url"}

        # 构建飞书消息卡片
        card = build_feishu_card(alert)
        payload = {"msg_type": "interactive", "card": card}

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(webhook_url, json=payload, timeout=10) as resp:
                    if resp.status != 200:
                        body = await resp.text()
                        return {"status": "failed", "error": f"HTTP {resp.status}: {body}"}
                    return {"status": "sent", "target": self.config.get("name", "feishu")}
            except Exception as e:
                return {"status": "failed", "error": str(e)}

    def validate_config(self) -> bool:
        return "webhook_url" in self.config and self.config["webhook_url"].startswith("https://open.feishu.cn")

def build_feishu_card(alert: AlertData) -> dict:
    """构造飞书消息卡片（简化版）"""
    return {
        "header": {
            "title": {"tag": "plain_text", "content": f"[{alert.severity.upper()}] {alert.name}"},
            "template": "red" if alert.severity == "critical" else "orange"
        },
        "elements": [
            {"tag": "markdown", "content": f"**状态**: {alert.status}\n**服务**: {alert.labels.get('service', 'N/A')}\n**描述**: {alert.annotations.get('description', '')}"},
            {"tag": "note", "elements": [{"tag": "plain_text", "content": f"开始时间: {alert.starts_at}"}]}
        ]
    }
```

**配置文件中注册（YAML）**:

```yaml
channels:
  - name: "ops-feishu"
    type: "feishu"
    webhook_url: "https://open.feishu.cn/open-apis/bot/v2/hook/xxxxx"
  - name: "dev-email"
    type: "email"
    smtp_host: "smtp.example.com"
    smtp_port: 587
    username: "alert@example.com"
    password: "secret"
    recipients: ["dev@example.com"]
```

---

## 4. 模板引擎接口

提供 `render(template, context)` 函数，用于将告警数据渲染为目标通道所需的格式（纯文本、HTML、JSON、消息卡片等）。模板使用 Jinja2 语法。

### 4.1 函数签名

```python
def render(template: str, context: dict) -> str:
    """
    渲染模板
    :param template: Jinja2 模板字符串
    :param context: 上下文变量字典
    :return: 渲染后的字符串
    """
```

### 4.2 使用说明

- 模板引擎内置常见过滤器和函数（如 `upper`, `dateformat`, `jsonify`）。
- 上下文 `context` 中始终包含 `alert`（AlertData 对象）和 `channel`（通道配置字典）。
- 建议将模板存储在独立文件中，通过配置加载。

**模板示例（邮件 HTML 模板）**:

```html
<html>
<body>
<h2>[{{ alert.severity|upper }}] {{ alert.name }}</h2>
<p><strong>状态:</strong> {{ alert.status }}</p>
<p><strong>服务:</strong> {{ alert.labels.get('service', 'N/A') }}</p>
<p><strong>描述:</strong> {{ alert.annotations.get('description', '') }}</p>
<p><strong>开始时间:</strong> {{ alert.starts_at }}</p>
<br/>
<a href="{{ alert.generator_url }}">查看详情</a>
</body>
</html>
```

**调用示例**:

```python
from your_alert_system.template import render

template = "Alert {{ alert.name }} is {{ alert.status }}"
context = {"alert": alert_data, "channel": {"name": "ops"}}
result = render(template, context)
# 输出: "Alert HighCPUUsage is firing"
```

### 4.3 内置过滤器

| 过滤器名 | 说明 | 示例 |
|----------|------|------|
| `upper` | 转大写 | `{{ alert.severity\|upper }}` → `CRITICAL` |
| `lower` | 转小写 | `{{ alert.status\|lower }}` → `firing` |
| `dateformat(format)` | 格式化日期 | `{{ alert.starts_at\|dateformat("YYYY-MM-DD HH:mm") }}` |
| `jsonify` | 将对象转为 JSON 字符串 | `{{ alert.labels\|jsonify }}` |

---

## 5. 配置加载器

提供 `load_config(path)` 函数，用于加载 YAML 格式的配置文件，返回标准化的配置字典。

### 5.1 函数签名

```python
def load_config(path: str) -> dict:
    """
    从文件路径加载配置
    :param path: 配置文件路径（支持 YAML 或 JSON）
    :return: 配置字典
    :raises FileNotFoundError: 文件不存在时
    :raises ValueError: 文件格式错误时
    """
```

### 5.2 返回结构

返回字典包含顶层字段：

| 字段 | 类型 | 描述 |
|------|------|------|
| `general` | dict | 通用配置，如 `listen_port`, `log_level` |
| `channels` | list[dict] | 通道列表，每个字典包含 `name`, `type` 及该通道特有参数 |
| `routing` | list[dict] | 路由规则：根据告警标签匹配通道 |
| `templates` | dict | 模板映射：`{channel_type: template_path}` |
| `auth` | dict | 认证配置，如 `api_key` |

**完整配置文件示例 (`config.yaml`)**:

```yaml
general:
  listen_port: 8080
  log_level: info
  max_retries: 3

channels:
  - name: "critical-feishu"
    type: "feishu"
    webhook_url: "https://open.feishu.cn/open-apis/bot/v2/hook/aBCdef"
  - name: "all-email"
    type: "email"
    smtp_host: "smtp.example.com"
    smtp_port: 587
    username: "alert@example.com"
    password: "${EMAIL_PASSWORD}"   # 支持环境变量引用
    recipients:
      - "oncall@example.com"
      - "alert-archive@example.com"
  - name: "custom-webhook"
    type: "webhook"
    url: "https://internal.example.com/webhook"
    method: "POST"
    headers:
      X-API-Key: "secret-key"

routing:
  - name: "critical-route"
    match:
      severity: "critical"
    channels: ["critical-feishu", "all-email"]
  - name: "default-route"
    match: {}
    channels: ["all-email"]

templates:
  feishu: "templates/feishu_card.j2"
  email: "templates/email.html"
  webhook: "templates/webhook.json"

auth:
  api_key: "${API_KEY}"   # 客户端调用接口时的认证密钥
```

**加载示例与输出（部分）**:

```python
config = load_config("config.yaml")
print(config["channels"][0]["webhook_url"])  # "https://open.feishu.cn/open-apis/bot/v2/hook/aBCdef"
print(config["routing"][0]["channels"])      # ["critical-feishu", "all-email"]
```

---

## 6. 状态接口

### 6.1 GET /health

用于健康检查，返回系统当前运行状态。

#### 6.1.1 响应格式

**HTTP 状态码**:  
- `200 OK`: 系统正常
- `503 Service Unavailable`: 系统不可用（如关键组件异常）

**响应体结构**:

| 字段 | 类型 | 描述 |
|------|------|------|
| `status` | string | `"ok"` 或 `"degraded"` 或 `"down"` |
| `version` | string | 当前系统版本 |
| `uptime_seconds` | int | 运行时长（秒） |
| `channels` | array | 已注册通道的状态列表 |
| `last_alert_received` | string | 最后一次