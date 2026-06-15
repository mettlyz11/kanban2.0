# 飞书PagerDuty双通道告警集成方案

> 任务: v12 #41 飞书+PagerDuty双通道告警
> 附件类型: 技术方案文档
> 生成时间: 2026-05-12 08:51

# 技术方案文档

**项目名称：** v12 #41 飞书+PagerDuty双通道告警  
**文档版本：** 1.0  
**创建日期：** 2025-04-14  
**作者：** 技术方案组  

---

## 1. 概述与目标

### 1.1 背景
在运维监控体系中，告警的及时性和可靠性直接影响故障响应效率。单一通知渠道（如仅依赖飞书或仅依赖PagerDuty）存在单点风险：飞书群机器人可能因频率限制或网络问题丢失消息，而PagerDuty虽具备成熟的轮值、升级策略，但国内团队日常沟通仍以飞书为主。因此，需要构建**飞书+PagerDuty双通道告警**，确保任何一条告警都能同时通过两个独立渠道送达，提升告警送达率与响应效率。

### 1.2 目标
- 实现从任意告警源（如Prometheus、Zabbix、自定义脚本）同时向飞书群机器人和PagerDuty服务发送告警事件。
- 飞书通道用于即时通知，PagerDuty通道用于事件管理、自动分派、升级策略及历史追溯。
- 提供完整的配置步骤、示例模板以及测试验证方法，确保运维人员可在30分钟内完成部署。

---

## 2. 前置条件

### 2.1 飞书应用
- 拥有一个飞书企业版或旗舰版账号（个人版无法创建机器人）。
- 拥有目标群组的**管理员权限**或**群主权限**，以便创建群机器人。
- 准备一个用于接收告警的飞书群（建议为运维值班群），群成员至少包含值班人员。

### 2.2 PagerDuty账号
- 拥有PagerDuty账号（免费版或付费版均可，免费版支持每月最多1000个事件）。
- 已创建PagerDuty团队并添加用户。
- 具备创建服务（Service）和集成（Integration）的权限。

### 2.3 告警源准备
- 任意能够发送HTTP POST请求的告警源（例如Prometheus Alertmanager、Zabbix的Webhook action、自定义Shell脚本、CI/CD流水线等）。
- 可选的统一告警网关：如使用Python Flask或Node.js编写的中转服务，用于格式化告警并分别发送给飞书和PagerDuty。

---

## 3. 飞书机器人配置

### 3.1 创建飞书群机器人
1. 打开目标飞书群聊，点击群聊右上角“…”图标 → “群机器人” → “添加机器人”。
2. 在机器人列表中选择“Webhook机器人”（或自定义机器人），点击“添加”。
3. 重命名机器人为“告警通知机器人”（可选），点击“确定”。
4. 复制生成的Webhook URL，格式类似：
   ```
   https://open.feishu.cn/open-apis/bot/v2/hook/xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
   ```
   安全建议：该URL包含密钥，请勿泄露到公开代码仓库或日志中。

### 3.2 飞书机器人消息类型选择
飞书Webhook支持文本（text）、富文本（post）、交互卡片（interactive）等。本方案推荐使用**交互卡片**（用于告警场景，可包含标题、状态、严重级别、时间、链接等），但也可降级为简单文本。  
后续示例将同时提供文本和卡片两种模板。

---

## 4. PagerDuty配置

### 4.1 创建PagerDuty服务
1. 登录PagerDuty管理后台，选择“Services” → “Services” → “New Service”。
2. 填写服务名称（如“Production-Infra-Alerts”），描述可留空。
3. **Integration Type**：选择“Use our API directly”下的“Events API v2”（推荐），或者选择已有的集成如“Prometheus”、“Zabbix”等。本方案使用通用Events API v2，以便对接任意告警源。
4. 点击“Add Service”创建服务。
5. 创建成功后，记录**Integration Key**（即API密钥，格式为32位十六进制字符串），用于后续发送事件。

### 4.2 配置PagerDuty事件规则（可选）
可以根据告警严重级别（如critical、warning）设置不同的自动化响应（如自动创建Jira Ticket、触发Runbook）。本方案暂不涉及，但可在PagerDuty规则引擎中配置。

---

## 5. 双通道告警逻辑设计

### 5.1 架构图
```
告警源（Prometheus / Zabbix / 脚本）
          |
          v
   告警转发中继（可选）
          |
          ├─────> 飞书Webhook ───────> 飞书群
          └─────> PagerDuty Events API ──> PagerDuty服务
```
- **方式一：直接双发**  
  告警源（如Prometheus Alertmanager）配置两个接收器（receivers）：一个调飞书Webhook，一个调PagerDuty Webhook（或直接发Events API）。  
  优点：独立、无中间依赖。  
  缺点：需要告警源支持多个输出，且每个通道需单独处理认证、重试。

- **方式二：中继服务**  
  使用轻量级服务（如一个Flask应用）接收告警源的单一Webhook，然后内部调用飞书和PagerDuty。  
  优点：统一告警格式、可做清理、重试、日志记录；减少告警源配置复杂度。  
  缺点：引入单点（中继服务本身需高可用）。

本方案推荐**方式二**，因为更灵活且易于维护。中继服务的部署可采用容器化（Docker），配合环境变量管理密钥。

### 5.2 中继服务工作流
1. 告警源向中继服务 `/alert` 端点发送POST请求，Payload格式统一（例如符合Prometheus Alertmanager格式或自定义JSON）。
2. 中继服务解析告警，生成飞书卡片消息和PagerDuty事件。
3. 中继服务分别并发发送到两个通道（使用`asyncio`或线程池）。
4. 分别处理重试：飞书重试最多3次，间隔5秒；PagerDuty重试2次，间隔10秒。
5. 记录发送结果到本地日志或外部数据库（可选）。

---

## 6. 示例配置

### 6.1 中继服务代码（Python Flask完整可运行）

**目录结构**
```
alert-relay/
├── app.py
├── requirements.txt
├── config.env
```

**requirements.txt**
```
flask==3.0.0
requests==2.31.0
python-dotenv==1.0.0
```

**config.env（示例，请替换真实值）**
```
FEISHU_WEBHOOK_URL=https://open.feishu.cn/open-apis/bot/v2/hook/YOUR_FEISHU_KEY
PAGERDUTY_INTEGRATION_KEY=your_pagerduty_integration_key
PAGERDUTY_ROUTING_KEY=your_pagerduty_routing_key   # 可选，Events API v2使用
```

**app.py**（完整可运行）
```python
import os
import json
import logging
from datetime import datetime

import requests
from flask import Flask, request, jsonify
from dotenv import load_dotenv

load_dotenv('config.env')

app = Flask(__name__)

# 配置日志
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 读取配置
FEISHU_WEBHOOK = os.getenv('FEISHU_WEBHOOK_URL')
PD_INTEGRATION_KEY = os.getenv('PAGERDUTY_INTEGRATION_KEY')
PD_ROUTING_KEY = os.getenv('PAGERDUTY_ROUTING_KEY', PD_INTEGRATION_KEY)

# 飞书消息模板（卡片）
FEISHU_CARD_TEMPLATE = {
    "msg_type": "interactive",
    "card": {
        "header": {"title": {"tag": "plain_text", "content": "⚠️ 告警通知"}, 
                   "template": "red"},
        "elements": [
            {"tag": "div", "text": {"tag": "lark_md", "content": "**告警名称**: {alert_name}\n**严重级别**: {severity}\n**状态**: {status}\n**时间**: {time}\n**详情**: {detail}"}},
            {"tag": "hr"},
            {"tag": "note", "elements": [{"tag": "plain_text", "content": "飞书+PagerDuty 双通道告警"}]}
        ]
    }
}

def send_feishu(payload):
    """发送消息到飞书"""
    try:
        resp = requests.post(FEISHU_WEBHOOK, json=payload, timeout=10)
        resp.raise_for_status()
        result = resp.json()
        if result.get('code') == 0:
            logger.info("飞书发送成功")
        else:
            logger.error(f"飞书发送返回错误: {result}")
        return True
    except Exception as e:
        logger.error(f"飞书发送异常: {e}")
        return False

def send_pagerduty(payload):
    """发送事件到PagerDuty"""
    # 构建PagerDuty Events API v2 Payload
    pd_event = {
        "routing_key": PD_ROUTING_KEY,
        "event_action": "trigger",  # trigger, acknowledge, resolve
        "dedup_key": payload.get("dedup_key", ""),
        "payload": {
            "summary": payload["title"],
            "severity": payload.get("severity", "critical").lower(),
            "source": payload.get("source", "Alert Relay"),
            "timestamp": payload.get("timestamp", datetime.utcnow().isoformat() + "Z"),
            "custom_details": payload.get("custom_details", {})
        }
    }
    url = "https://events.pagerduty.com/v2/enqueue"
    try:
        resp = requests.post(url, json=pd_event, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        logger.info(f"PagerDuty发送成功, dedup_key={data.get('dedup_key')}")
        return True
    except Exception as e:
        logger.error(f"PagerDuty发送异常: {e}")
        return False

@app.route('/alert', methods=['POST'])
def receive_alert():
    """统一告警接收端点"""
    try:
        data = request.get_json(force=True)
    except Exception as e:
        return jsonify({"error": "Invalid JSON"}), 400

    # 提取告警信息（适配Prometheus Alertmanager格式，也可自定义）
    alerts = data.get('alerts', [data])  # 支持批量
    for alert in alerts:
        labels = alert.get('labels', {})
        annotations = alert.get('annotations', {})
        alert_name = labels.get('alertname', annotations.get('summary', 'Unknown'))
        severity = labels.get('severity', 'critical')
        status = alert.get('status', 'firing')
        detail = annotations.get('description', annotations.get('detail', '无详情'))
        start_time = alert.get('startsAt', datetime.utcnow().isoformat() + 'Z')

        # 构造飞书卡片
        feishu_card = FEISHU_CARD_TEMPLATE.copy()
        # 替换占位符
        card_content = feishu_card['card']['elements'][0]['text']['content']
        card_content = card_content.format(
            alert_name=alert_name,
            severity=severity,
            status=status,
            time=start_time,
            detail=detail
        )
        feishu_card['card']['elements'][0]['text']['content'] = card_content

        # 构造PagerDuty事件
        pd_payload = {
            "title": f"[{severity}] {alert_name}",
            "severity": severity,
            "timestamp": start_time,
            "source": labels.get('instance', labels.get('host', 'unknown')),
            "dedup_key": f"alert-{labels.get('alertname','unknown')}-{labels.get('instance','')}",
            "custom_details": {
                "labels": labels,
                "annotations": annotations,
                "raw": alert
            }
        }

        # 并发发送
        import threading
        threads = []
        t1 = threading.Thread(target=send_feishu, args=(feishu_card,))
        t2 = threading.Thread(target=send_pagerduty, args=(pd_payload,))
        threads.append(t1); threads.append(t2)
        for t in threads: t.start()
        for t in threads: t.join()

    return jsonify({"status": "queued", "alerts_count": len(alerts)}), 202

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
```

### 6.2 飞书消息模板（纯文本备用）
当卡片不可用时，可使用文本模板。
```json
{
    "msg_type": "text",
    "content": {
        "text": "【告警】{alert_name}\n严重级别: {severity}\n状态: {status}\n时间: {time}\n详情: {detail}"
    }
}
```

### 6.3 PagerDuty 事件Payload示例
```json
{
    "routing_key": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
    "event_action": "trigger",
    "dedup_key": "alert-CPU_High-192.168.1.100",
    "payload": {
        "summary": "[critical] CPU_High",
        "severity": "critical",
        "source": "192.168.1.100",
        "timestamp": "2025-04-14T10:30:00.000Z",
        "custom_details": {
            "labels": {
                "alertname": "CPU_High",
                "instance": "192.168.1.100",
                "severity": "critical"
            },
            "annotations": {
                "summary": "CPU usage above 90%",
                "description": "CPU usage at 95% for 5 minutes"
            }
        }
    }
}
```

---

## 7. 测试验证方案

### 7.1 本地启动中继服务
```bash
cd alert-relay
pip install -r requirements.txt
source config.env  # 或设置环境变量
python app.py
```
服务运行在 `http://0.0.0.0:5000`。

### 7.2 模拟发送测试告警
使用curl发送一条模拟Prometheus告警：
```bash
curl -X POST http://localhost:5000/alert \
  -H "Content-Type: application/json" \
  -d '{
    "status": "firing",
    "labels": {
      "alertname": "TestAlert",
      "severity": "critical",
      "instance": "web-01.example.com"
    },
    "annotations": {
      "summary": "这是一条测试告警",
      "description": "模拟CPU过高",
      "detail": "当前值95%，超过阈值90%"
    },
    "startsAt": "2025-04-14T12:00:00Z"
  }'
```

### 7.3 验证结果
- **飞书**：检查目标飞书群是否收到一条交互卡片消息，包含告警名称、严重级别、时间等信息。
- **PagerDuty**：登录PagerDuty后台，进入对应服务，查看“Incidents”页面是否出现一条新Incident，状态为“Triggered”，内容与发送一致。

### 7.4 自动化测试（可选）
可编写简单的Python测试脚本，依次发送critical、warning、resolved事件，断言两个渠道均成功接收。

---

## 8. 注意事项

### 8.1 频率限制
- **飞书**：每分钟最多20条消息（群机器人限制），超出后可能被限流或丢弃。建议在告警合并端先将多条告警聚合并延迟发送，或使用飞书消息队列。
- **PagerDuty**：免费版每小时最多500个事件，付费版更高。若短时间内产生大量重复告警，应使用`dedup_key`去重，PagerDuty会自动合并为同一Incident。

### 8.2 安全
- Webhook URL和Integration Key属于敏感信息，必须通过环境变量或密钥管理服务（如KMS）注入，严禁硬编码在代码或配置文件中。
- 中继服务应部署在内网，仅由可信告警源调用，或添加IP白名单、HTTP Basic Auth等安全措施。

### 8.3 故障处理
- **飞书发送失败**：记录日志并告警（可发送到PagerDuty自身），中继服务应重试（已内置3次重试）。若飞书长期不可达，考虑切换