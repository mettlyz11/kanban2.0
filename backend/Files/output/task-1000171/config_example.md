# config_example

> 任务: v8 #20 可配置告警通道 — feishu/email/webhook
> 附件类型: 配置文件
> 生成时间: 2026-05-12 06:56

```yaml
# ============================================================
#  可配置告警通道 — 全局配置文件
#  版本: v8 #20
#  用途: 定义飞书、邮件、Webhook 通道的详细参数及路由规则
# ============================================================

# ------------------------------------------------------------
# 全局配置
# ------------------------------------------------------------
global:
  # 服务监听地址和端口
  server:
    host: "0.0.0.0"
    port: 8080

  # 日志级别: debug / info / warn / error / fatal
  log_level: "info"

  # 告警去重窗口（秒），相同告警在窗口内仅发送一次
  dedup_window: 300

  # 健康检查路径
  health_check:
    path: "/health"
    enabled: true

  # 通道发送失败时的重试策略
  retry:
    max_attempts: 3
    initial_interval: 5s
    multiplier: 2.0
    max_interval: 60s

# ------------------------------------------------------------
# 飞书通道配置
# ------------------------------------------------------------
feishu_channels:
  # 默认飞书告警机器人
  - name: "default-feishu"
    enabled: true
    # 飞书 Webhook URL (必须)
    webhook_url: "https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
    # 签名校验密钥 (可选，若飞书机器人开启了签名校验)
    secret: "your-feishu-signing-secret-key"
    # 自定义请求头 (可选，用于代理或认证)
    extra_headers:
      X-Request-Source: "alert-system"
      X-Custom-Tag: "production"
    # 发送时的默认消息格式: text / markdown / interactive (卡片)
    msg_type: "interactive"
    # 消息模板 (若不指定则使用全局模板)
    template: "templates/feishu_alarm_card.json"

  # 紧急告警专用飞书通道 (仅接收 P0 级别告警)
  - name: "critical-feishu"
    enabled: true
    webhook_url: "https://open.feishu.cn/open-apis/bot/v2/hook/yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy"
    secret: "critical-feishu-secret-2024"
    msg_type: "interactive"
    template: "templates/feishu_critical_card.json"
    # 限制该通道仅用于特定告警容器
    labels:
      severity: "P0"

# ------------------------------------------------------------
# 邮件通道配置
# ------------------------------------------------------------
email_channels:
  - name: "default-email"
    enabled: true
    smtp:
      # SMTP 服务器地址 (支持 TLS/STARTTLS)
      server: "smtp.example.com"
      port: 587
      # 使用 STARTTLS (true) 还是直接 SSL (false, 通常端口465)
      starttls: true
      # 超时时间
      timeout: 30s
      # 认证信息 (支持 PLAIN / LOGIN / CRAM-MD5)
      auth:
        user: "alert@example.com"
        password: "smtp-secret-password-123"
    # 发件人地址
    from: "Alert System <alert@example.com>"
    # 收件人列表 (支持多个, 半角逗号分隔或数组)
    recipients:
      - "ops-team@example.com"
      - "oncall@example.com"
    # 主题模板 (支持变量: {{.alert_name}}, {{.severity}}, {{.timestamp}})
    subject_template: "[{{.severity}}] {{.alert_name}} - {{.timestamp}}"
    # 正文模板 (可使用 Go 模板语法)
    body_template: "templates/email_alarm.html"   # 文件路径，若不存在则使用下方内联模板
    # 内联模板 (当 body_template 文件不存在时使用)
    body_inline: |
      <h2>告警详情</h2>
      <table border="1">
        <tr><td>名称</td><td>{{.alert_name}}</td></tr>
        <tr><td>级别</td><td>{{.severity}}</td></tr>
        <tr><td>时间</td><td>{{.timestamp}}</td></tr>
        <tr><td>描述</td><td>{{.description}}</td></tr>
      </table>
      <hr>
      <p>请及时处理。</p>

  # 用于低优先级通知的邮件通道 (仅发送 P3/P4)
  - name: "low-priority-email"
    enabled: true
    smtp:
      server: "smtp-low.example.com"
      port: 25
      starttls: false
      timeout: 15s
      auth:
        user: "noreply@example.com"
        password: "noreply-pass-abc"
    from: "No Reply <noreply@example.com>"
    recipients:
      - "info@example.com"
    subject_template: "[通知] {{.alert_name}}"
    body_inline: |
      告警名称: {{.alert_name}}
      级别: {{.severity}}
      时间: {{.timestamp}}
      详情: {{.description}}

# ------------------------------------------------------------
# Webhook 通道配置
# ------------------------------------------------------------
webhook_channels:
  - name: "default-webhook"
    enabled: true
    # 目标 URL (支持 HTTP/HTTPS)
    target_url: "https://hooks.example.com/alert"
    # HTTP 方法: GET / POST / PUT / PATCH
    method: "POST"
    # 超时时间
    timeout: 10s
    # 自定义请求头
    headers:
      Content-Type: "application/json"
      Authorization: "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
      X-Request-ID: "{{.alert_id}}"     # 支持模板变量
    # 请求体模板 (使用 Go 模板, 最终生成 JSON 或 XML)
    body_template: |
      {
        "alert_id": "{{.alert_id}}",
        "alert_name": "{{.alert_name}}",
        "severity": "{{.severity}}",
        "status": "{{.status}}",
        "timestamp": "{{.timestamp}}",
        "labels": {
          {{- range $key, $value := .labels }}
          "{{$key}}": "{{$value}}"{{- if not (last $key) }},{{- end }}
          {{- end }}
        },
        "annotations": {
          {{- range $key, $value := .annotations }}
          "{{$key}}": "{{$value}}"{{- if not (last $key) }},{{- end }}
          {{- end }}
        },
        "description": "{{.description}}",
        "source": "{{.source}}"
      }
    # 响应处理: 可选丢弃/记录/重试
    response:
      success_codes: [200, 201, 202]
      retry_on_failure: true
      log_response_body: true

  # Prometheus Alertmanager 风格的 Webhook 通道
  - name: "prometheus-webhook"
    enabled: true
    target_url: "http://alertmanager:9093/api/v1/alerts"
    method: "POST"
    headers:
      Content-Type: "application/json"
    body_template: |
      [
        {
          "labels": {
            "alertname": "{{.alert_name}}",
            "severity": "{{.severity}}",
            "instance": "{{index .labels "instance"}}"
          },
          "annotations": {
            "summary": "{{.description}}",
            "runbook_url": "{{index .annotations "runbook_url"}}"
          },
          "startsAt": "{{.startsAt}}",
          "endsAt": "{{.endsAt}}",
          "generatorURL": "{{.generatorURL}}"
        }
      ]

# ------------------------------------------------------------
# 路由规则配置
# ------------------------------------------------------------
# 根据告警的 severity 或 labels 匹配对应通道。
# 规则按顺序匹配，第一个匹配的规则生效。
# 每个规则可以指定一个或多个通道 (支持飞书/邮件/Webhook 的 name)。
routes:
  # 所有 P0 级别告警 => 发送到 critical-feishu + default-email + default-webhook
  - match:
      severity: "P0"
    channels:
      - "critical-feishu"
      - "default-email"
      - "default-webhook"
    # 可选: 是否继续匹配后续规则 (默认 false)
    continue: false

  # 所有 P1 级别告警 => 发送到 default-feishu + default-email
  - match:
      severity: "P1"
    channels:
      - "default-feishu"
      - "default-email"
    continue: false

  # 所有 P2 级别告警 => 仅发送到 default-feishu + default-webhook
  - match:
      severity: "P2"
    channels:
      - "default-feishu"
      - "default-webhook"

  # 标签匹配: 包含 "environment: production" 的告警 => 额外发送到 default-webhook
  - match:
      labels:
        environment: "production"
    channels:
      - "default-webhook"
    # 注意: 此规则会追加到之前匹配的通道 (因为 continue: true)
    continue: true

  # 默认兜底规则：所有未匹配的告警 => 发送到 default-feishu + low-priority-email
  - match:
      severity: ".*"     # 正则表达式
    channels:
      - "default-feishu"
      - "low-priority-email"

# ------------------------------------------------------------
# 模板配置
# ------------------------------------------------------------
# 这里定义全局可用的消息模板，支持文件路径或内联定义。
# 各通道可以在配置中引用具体模板名称。
templates:
  # 飞书交互式卡片模板 (JSON)
  - name: "feishu_alarm_card.json"
    type: "file"
    path: "/etc/alert/templates/feishu_alarm_card.json"

  # 飞书紧急告警卡片 (内联)
  - name: "feishu_critical_card.json"
    type: "inline"
    content: |
      {
        "msg_type": "interactive",
        "content": {
          "elements": [
            {
              "tag": "div",
              "text": {
                "tag": "lark_md",
                "content": "**【紧急告警】{{.alert_name}}**\n级别: **P0**\n时间: {{.timestamp}}\n描述: {{.description}}"
              }
            },
            {
              "tag": "hr"
            },
            {
              "tag": "note",
              "text": {
                "tag": "plain_text",
                "content": "请立即处理！"
              }
            }
          ]
        }
      }

  # 邮件 HTML 模板 (文件)
  - name: "email_alarm.html"
    type: "file"
    path: "/etc/alert/templates/email_alarm.html"

  # Webhook 默认请求体模板 (内联, 已在 webhook 通道中定义)
  # 此处仅为参考，通道配置中的 body_template 优先级更高
  - name: "webhook_default.json"
    type: "inline"
    content: |
      {
        "alert_name": "{{.alert_name}}",
        "severity": "{{.severity}}",
        "status": "{{.status}}"
      }

# ------------------------------------------------------------
# 附加配置: 发送频率限制、黑名单、白名单等
# ------------------------------------------------------------
rate_limit:
  # 每个通道每秒最多发送数 (0 为不限制)
  per_channel: 10
  # 全局每秒最多发送数
  global: 50

# 告警内容中的敏感信息过滤 (支持正则替换)
sanitize:
  - field: "description"
    pattern: "(password|token|secret)=\\S+"
    replacement: "[REDACTED]"
  - field: "annotations"
    pattern: "(api_key|private_key):\\s*\\S+"
    replacement: "$1: [REDACTED]"

# 告警静默规则 (匹配到的告警会被忽略)
silences:
  - match:
      alert_name: "CPU_Usage_High"
      severity: "P3"
    until: "2025-12-31T23:59:59Z"
    comment: "已知问题，正在修复"
  - match:
      labels:
        service: "monitoring"
    until: "2026-01-01T00:00:00Z"
    comment: "监控系统自身告警静默"
```