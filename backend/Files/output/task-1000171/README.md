# README

> 任务: v8 #20 可配置告警通道 — feishu/email/webhook
> 附件类型: 用户手册
> 生成时间: 2026-05-12 06:57

# v8 #20 可配置告警通道 — feishu/email/webhook 用户手册

---

## 1. 项目简介与功能概述

**v8 #20 可配置告警通道** 是一个轻量级的告警通知分发服务，旨在接收来自 Prometheus AlertManager 或其他告警源的 Webhook 请求，并将告警消息通过可配置的通道（目前支持飞书机器人、SMTP 邮件、通用 Webhook）实时推送给运维或开发人员。

### 功能特性
- **多通道并行**：可同时启用飞书、Email、自定义 Webhook，每条告警可选择通知到所有已配置通道。
- **动态配置**：通过 YAML 配置文件管理通道参数，无需重启服务即可通过信号重载配置。
- **模板系统**：使用 Go 模板语法（或 Python Jinja2 兼容）定义告警消息格式，支持自定义标题、内容、颜色等。
- **健康检查**：内置 HTTP 端点 `/health` 和 `/ready`，方便容器化部署。
- **报警分组与去重**：支持基于告警标签的分组，避免相同告警重复发送。
- **扩展架构**：通过实现标准通道接口，可快速集成钉钉、企业微信、Slack 等新通道。

本手册将引导您完成从安装、配置到生产部署的全流程。

---

## 2. 环境要求

本应用基于 Python 3.9+ 开发，建议使用官方最新稳定版。以下为硬性依赖：

| 依赖项        | 版本要求   | 用途                     |
|---------------|------------|--------------------------|
| Python        | >= 3.9     | 运行时环境               |
| Flask         | >= 2.2     | HTTP 服务框架            |
| PyYAML        | >= 6.0     | 配置文件解析             |
| requests      | >= 2.28    | 发送 HTTP 请求           |
| Jinja2        | >= 3.1     | 模板渲染引擎             |
| openpyxl      | >= 3.0     | (可选) Excel 日志导出    |

### 操作系统
- Linux (Ubuntu 20.04+, CentOS 7+)
- macOS ( Monterey+ )
- Windows (需要 WSL 或原生 Python，本手册以 Linux 为准)

### 安装依赖

```bash
# 创建并激活虚拟环境（推荐）
python3 -m venv venv
source venv/bin/activate

# 安装核心依赖
pip install flask pyyaml requests jinja2

# 如果使用邮件通道，还需要安装：
pip install secure-smtplib

# 验证安装
python -c "import flask; import yaml; print('OK')"
```

---

## 3. 快速开始

### 3.1 下载项目

```bash
git clone https://github.com/your-org/alert-channel-gateway.git
cd alert-channel-gateway
```

项目结构：

```
alert-channel-gateway/
├── app.py                  # 主入口，Flask 应用
├── config.yaml             # 主配置文件
├── channels/               # 通道实现
│   ├── __init__.py
│   ├── base.py             # 抽象基类
│   ├── feishu.py           # 飞书通道
│   ├── email.py            # 邮件通道
│   └── webhook.py          # 通用 Webhook 通道
├── templates/              # 告警模板文件夹
│   ├── feishu.json.j2      # 飞书消息模板
│   ├── email.html.j2       # 邮件 HTML 模板
│   └── webhook.json.j2     # 通用 Webhook 模板
├── requirements.txt
└── README.md
```

### 3.2 配置基础参数

编辑 `config.yaml`，以下是一个最小化配置示例：

```yaml
server:
  host: "0.0.0.0"
  port: 8080
  debug: false

channels:
  feishu:
    enabled: true
    webhook_url: "https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxxxxx"
    secret: ""                  # 可选，签名校验密钥
  email:
    enabled: true
    smtp_host: "smtp.qq.com"
    smtp_port: 465
    smtp_ssl: true
    sender: "alert@example.com"
    password: "your_smtp_password"
    receivers:
      - "ops@example.com"
      - "dev@example.com"
    subject_prefix: "[告警]"
  webhook:
    enabled: false
    url: "http://internal-webhook:9000/alert"
    headers:
      Authorization: "Bearer token123"
    method: "POST"

alert_grouping:
  labels: ["alertname", "severity"]   # 按这些标签分组
  group_wait: 30s                      # 同一组等待时间
  group_interval: 5m                   # 组内重复间隔
  repeat_interval: 4h                  # 重复发送间隔

templates:
  default: "templates/feishu.json.j2"  # 默认模板路径
```

### 3.3 启动服务

```bash
python app.py
```

输出如下表示启动成功：

```
 * Serving Flask app 'app'
 * Debug mode: off
 * Running on all addresses (0.0.0.0)
 * Running on http://127.0.0.1:8080
```

### 3.4 发送测试告警

使用 `curl` 模拟 AlertManager Webhook：

```bash
curl -X POST http://localhost:8080/api/v1/alert \
  -H "Content-Type: application/json" \
  -d '{
    "receiver":"webhook",
    "status":"firing",
    "alerts":[
      {
        "status":"firing",
        "labels":{
          "alertname":"NodeHighMemory",
          "instance":"192.168.1.10",
          "severity":"critical"
        },
        "annotations":{
          "summary":"Node memory usage > 90%",
          "description":"Memory usage on 192.168.1.10 is 95%"
        },
        "startsAt":"2025-04-01T10:00:00Z"
      }
    ],
    "groupLabels":{"alertname":"NodeHighMemory"},
    "commonLabels":{"severity":"critical"}
  }'
```

检查飞书群或邮箱是否收到告警消息。若收到，则安装成功。

---

## 4. 配置详解

### 4.1 全局配置 `config.yaml`

所有配置项以 YAML 格式编写，系统启动时自动加载。支持热重载：向进程发送 `SIGHUP` 信号（仅 Linux）或调用 `POST /reload` 端点。

#### 4.1.1 服务器配置

```yaml
server:
  host: "0.0.0.0"         # 监听地址，生产环境建议绑定内网 IP
  port: 8080               # 监听端口
  debug: false             # 开启后输出详细日志，仅供调试
  log_level: "INFO"        # DEBUG, INFO, WARNING, ERROR
  reload_endpoint: true    # 是否启用 /reload 端点
```

#### 4.1.2 通道配置

每个通道都有独立的 `enabled` 开关和其他特定参数。

**飞书通道**：

| 参数           | 类型   | 必填 | 说明                                                         |
|----------------|--------|------|--------------------------------------------------------------|
| enabled        | bool   | 是   | 是否启用                                                     |
| webhook_url    | string | 是   | 飞书群机器人 Webhook 地址，从飞书群设置中获取                 |
| secret         | string | 否   | 签名校验密钥，如果启用了安全设置则必填                       |
| timeout        | int    | 否   | HTTP 请求超时秒数，默认 10                                   |

飞书消息格式：服务会通过模板渲染出 JSON，符合飞书消息卡片或文本格式。

**邮件通道**：

| 参数           | 类型   | 必填 | 说明                                                         |
|----------------|--------|------|--------------------------------------------------------------|
| enabled        | bool   | 是   | 是否启用                                                     |
| smtp_host      | string | 是   | SMTP 服务器地址，如 smtp.qq.com                              |
| smtp_port      | int    | 是   | 端口，465 对应 SSL，587 对应 STARTTLS                       |
| smtp_ssl       | bool   | 是   | 是否使用 SSL                                                 |
| sender         | string | 是   | 发件人邮箱                                                   |
| password       | string | 是   | 邮箱的 SMTP 授权码（非登录密码）                             |
| receivers      | list   | 是   | 收件人邮箱列表                                               |
| subject_prefix | string | 否   | 邮件主题前缀，如 `[告警]`                                    |
| content_type   | string | 否   | `html` 或 `text`，默认 `html`                                |

**通用 Webhook 通道**：

| 参数           | 类型   | 必填 | 说明                                                         |
|----------------|--------|------|--------------------------------------------------------------|
| enabled        | bool   | 是   | 是否启用                                                     |
| url            | string | 是   | 目标 URL                                                     |
| method         | string | 否   | 请求方法，默认 `POST`，可选 `PUT`                            |
| headers        | dict   | 否   | 自定义请求头，如 `Authorization`                             |
| timeout        | int    | 否   | 超时秒数，默认 10                                            |

#### 4.1.3 分组与去重

```yaml
alert_grouping:
  labels: ["alertname", "severity"]     # 用于分组的标签键列表
  group_wait: 30s                        # 新组等待时间，在此时间内收集同组告警
  group_interval: 5m                     # 同组告警发送的最小间隔
  repeat_interval: 4h                    # 持续告警重复发送间隔
```

时间单位支持 `s`、`m`、`h`、`d`。

#### 4.1.4 模板配置

```yaml
templates:
  default: "templates/feishu.json.j2"    # 默认模板，无通道特定模板时使用
  feishu: "templates/feishu.json.j2"     # 可覆盖特定通道模板
  email: "templates/email.html.j2"
  webhook: "templates/webhook.json.j2"
```

### 4.2 环境变量覆盖

所有配置项均可通过环境变量覆盖，前缀为 `ALERTGW_`，下划线代替点号。例如：

```bash
export ALERTGW_SERVER_PORT=9090
export ALERTGW_CHANNELS_FEISHU_ENABLED=true
export ALERTGW_CHANNELS_EMAIL_RECEIVERS='["admin@example.com"]'  # JSON 数组字符串
```

---

## 5. 集成 AlertManager

本服务默认监听 `/api/v1/alert` 端点，与 AlertManager 的 `webhook_configs` 完全兼容。在 AlertManager 配置文件 `alertmanager.yml` 中添加 receiver：

```yaml
receivers:
- name: 'alert-channel-gateway'
  webhook_configs:
  - url: 'http://your-ip:8080/api/v1/alert'
    send_resolved: true            # 是否发送恢复通知
    http_config:
      timeout: 10s
```

重启 AlertManager 使配置生效：

```bash
systemctl restart alertmanager
```

### 验证集成

一旦 Prometheus 触发告警，AlertManager 将自动调用本服务。你可以在本服务的日志中看到请求记录：

```
2025-04-01 10:15:23 INFO [channel_gateway] Received alert: NodeHighMemory, status=firing
2025-04-01 10:15:23 INFO [feishu] Sending alert to Feishu: NodeHighMemory
2025-04-01 10:15:23 INFO [feishu] Feishu response status: 200
```

---

## 6. 自定义模板

模板使用 Jinja2 语法，渲染时的上下文包含以下变量：

| 变量        | 说明                                                         |
|-------------|--------------------------------------------------------------|
| alerts      | 告警列表，每个元素为 AlertManager 的 alert 对象               |
| status      | 当前状态：`firing` 或 `resolved`                              |
| groupLabels | 分组标签字典                                                 |
| commonLabels| 所有告警共有的标签字典                                       |
| receiver    | Receiver 名称（来自 AlertManager）                            |

### 6.1 飞书模板示例（`templates/feishu.json.j2`）

```json
{
    "msg_type": "interactive",
    "card": {
        "header": {
            "title": {
                "tag": "plain_text",
                "content": "{% if status == 'firing' %}🔥 告警触发{% else %}✅ 告警恢复{% endif %}"
            },
            "template": "{% if status == 'firing' %}red{% else %}green{% endif %}"
        },
        "elements": [
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": "**告警名称**: {{ alerts[0].labels.alertname }}\n**级别**: {{ alerts[0].labels.severity }}\n**实例**: {{ alerts[0].labels.instance }}\n**详情**: {{ alerts[0].annotations.description }}\n**时间**: {{ alerts[0].startsAt }}"
                }
            }
        ]
    }
}
```

### 6.2 邮件模板示例（`templates/email.html.j2`）

```html
<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><title>{{ alerts[0].labels.alertname }}</title></head>
<body>
<h2>{% if status == 'firing' %}🚨 告警通知{% else %}✅ 告警恢复{% endif %}</h2>
<table border="1" cellpadding="5" style="border-collapse:collapse;">
    <tr><th>属性</th><th>值</th></tr>
    <tr><td>告警名称</td><td>{{ alerts[0].labels.alertname }}</td></tr>
    <tr><td>级别</td><td>{{ alerts[0].labels.severity }}</td></tr>
    <tr><td>实例</td><td>{{ alerts[0].labels.instance }}</td></tr>
    <tr><td>描述</td><td>{{ alerts[0].annotations.description }}</td></tr>
    <tr><td>开始时间</td><td>{{ alerts[0].startsAt }}</td></tr>
</table>
</body>
</html>
```

### 6.3 使用模板注意事项

- 模板文件必须为 UTF-8 编码。
- 如果某个通道的模板文件不存在，将使用 `templates.default` 指定的默认模板。
- 可以在模板中使用 Jinja2 过滤器，例如 `{{ alerts | length }}`。

---

## 7. 扩展开发：如何添加新通道

本系统采用策略模式，通过实现一个基类即可添加任意通知通道。

### 7.1 通道接口

所有通道必须继承 `channels.base.BaseChannel` 并实现以下方法：

- `__init__(self, config: dict)`：接收该通道在 `config.yaml` 中的配置字典。
- `send(self, alert_group: dict) -> bool`：发送告警，返回成功与否。

### 7.2 示例：添加钉钉通道

在 `channels/` 下创建 `dingtalk.py`：

```python
from channels.base import BaseChannel
import requests
import json

class DingTalkChannel(BaseChannel):
    def __init__(self, config):
        super().__init__(config)
        self.webhook_url = config['webhook_url']
        self.timeout = config.get('timeout', 10)

    def send(self, alert_group):
        # 构建钉钉消息（Markdown格式）
        alerts = alert_group['alerts']
        status = alert_group['status']
        title = "告警触发" if status == "firing" else "告警恢复"
        text = f"### {title}\n"
        for a in alerts:
            text += f"- **{a['labels']['alertname']}** (等级: {a['labels'].get('severity', 'unknown')})\n"
            text += f"  - 实例: {a['labels'].get('instance', 'N/A')}\n"
            text += f"  - 描述: {a['annotations'].get('description', '')}\n"
        payload = {
            "msg