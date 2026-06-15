# multi_channel_access_api_specification

> 任务: 设计多channel信息接入模块 [04291942]
> 附件类型: API文档
> 生成时间: 2026-05-04 16:24

# 多Channel信息接入模块 API 文档

**文档版本**：v1.0  
**发布日期**：2024-06-15  
**最后更新**：2024-06-20  
**文档状态**：正式发布  
**维护团队**：消息中台团队  

---

## 1. 概览与版本

### 1.1 文档目的

本文档定义了多Channel信息接入模块（Multi-Channel Message Ingestion Module）对外暴露的接口规范。该模块作为统一的消息接入层，支持多种外部渠道（Channel）的消息接收、验证、标准化转换及路由分发。通过本模块，前端应用、第三方服务及内部系统可以以统一的规范向平台提交消息，实现渠道无关的消息集成。

### 1.2 模块定位

- **功能定位**：接收来自不同外部渠道（如短信网关、邮件服务器、即时通讯平台、IoT设备网关等）的原始消息，进行格式校验、内容转换、去重过滤后，推送至下游消息处理管道。
- **核心能力**：多协议支持（HTTP/HTTPS）、动态渠道注册、消息格式标准化、鉴权代理、流量控制、错误重试。

### 1.3 版本历史

| 版本 | 日期       | 变更说明                     | 作者     |
|------|------------|------------------------------|----------|
| v0.1 | 2024-05-01 | 初始草案                     | 张工     |
| v1.0 | 2024-06-15 | 正式发布，新增错误码规范     | 李四     |
| v1.1 | 2024-06-20 | 修正Webhook订阅接口路径      | 王五     |

### 1.4 基础URL

- **生产环境**：`https://api.example.com/v1`
- **测试环境**：`https://sandbox-api.example.com/v1`

所有API请求均需要包含 `Content-Type: application/json` 头部。

---

## 2. 认证与鉴权方式

### 2.1 认证机制

本模块采用 **API Key + HMAC签名** 双重认证机制。所有请求必须携带以下HTTP头部：

| 头部名称           | 必需 | 说明                                      |
|--------------------|------|-------------------------------------------|
| `X-API-Key`        | 是   | 分配给调用方的唯一API密钥                  |
| `X-Timestamp`      | 是   | Unix时间戳（秒），误差不超过300秒         |
| `X-Signature`      | 是   | HMAC-SHA256签名，对请求body进行签名        |
| `X-Nonce`          | 否   | 防重放攻击的一次性随机字符串（推荐使用）  |

### 2.2 签名生成算法

1. 准备待签名字符串 `stringToSign`：
   ```
   stringToSign = HTTP_METHOD + "\n" + PATH + "\n" + X-Timestamp + "\n" + X-Nonce(可选) + "\n" + REQUEST_BODY
   ```
2. 使用HMAC-SHA256算法，以API Secret为密钥对 `stringToSign` 计算签名。
3. 将签名结果进行Base64编码。

**Python示例**：
```python
import hmac
import hashlib
import base64
import time

def generate_signature(api_secret: str, method: str, path: str, body: str, timestamp: int, nonce: str = "") -> str:
    string_to_sign = f"{method}\n{path}\n{timestamp}\n{nonce}\n{body}"
    hmac_obj = hmac.new(api_secret.encode('utf-8'), string_to_sign.encode('utf-8'), hashlib.sha256)
    return base64.b64encode(hmac_obj.digest()).decode('utf-8')

# 使用示例
api_secret = "your-api-secret-here"
signature = generate_signature("POST", "/v1/channels/email/messages", '{"text":"Hello"}', int(time.time()))
print(signature)
```

### 2.3 密钥管理

- 每个调用方（应用/服务）会获得一对 `API Key` 和 `API Secret`。
- 密钥通过安全渠道（如控制台页面）分发，建议每90天轮换一次。
- 调用方需妥善保管 `API Secret`，平台端仅存储 `API Key` 的哈希值。

---

## 3. 消息接入API

### 3.1 提交消息到指定渠道

**端点**：`POST /api/v1/channels/{type}/messages`  

**路径参数**：

| 参数名 | 类型   | 必需 | 说明                                                                 |
|--------|--------|------|----------------------------------------------------------------------|
| type   | string | 是   | 渠道类型标识符。预定义值：`email`, `sms`, `webhook`, `wechat`, `iot` |

**请求体**（JSON）：

| 字段名      | 类型   | 必需 | 说明                                               |
|-------------|--------|------|----------------------------------------------------|
| source_id   | string | 是   | 调用方侧的消息唯一ID，用于去重和追踪               |
| content     | object | 是   | 消息内容，根据渠道类型有不同的结构（详见第5章）    |
| priority    | int    | 否   | 消息优先级，1-5，默认为3（1最高，5最低）           |
| metadata    | object | 否   | 自定义元数据，键值对形式，最大支持10个字段         |
| callback_url| string | 否   | 异步处理结果回调URL，若不提供则通过Webhook通知     |

**响应**（HTTP 201 Created）：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "message_id": "msg_20240620A3bC9dEf",
    "channel_type": "email",
    "status": "accepted",
    "created_at": "2024-06-20T10:30:00Z"
  }
}
```

**说明**：
- 返回的 `message_id` 为全局唯一消息标识，可用于后续查询状态。
- `status` 可能值为 `accepted`（已接受待处理）、`rejected`（被拒绝，见错误码）。
- 消息提交为异步处理，最终处理结果将通过回调或Webhook通知。

### 3.2 查询消息状态

**端点**：`GET /api/v1/channels/{type}/messages/{message_id}`  

**路径参数**：

| 参数名     | 类型   | 必需 | 说明                 |
|------------|--------|------|----------------------|
| type       | string | 是   | 渠道类型             |
| message_id | string | 是   | 消息唯一ID           |

**响应**（HTTP 200 OK）：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "message_id": "msg_20240620A3bC9dEf",
    "source_id": "ext-msg-001",
    "channel_type": "email",
    "status": "delivered",
    "delivery_detail": {
      "attempts": 2,
      "last_attempt": "2024-06-20T10:31:15Z",
      "error": null
    },
    "created_at": "2024-06-20T10:30:00Z",
    "updated_at": "2024-06-20T10:31:15Z"
  }
}
```

**状态枚举**：

| 状态         | 说明                           |
|--------------|--------------------------------|
| accepted     | 已接收，等待处理               |
| processing   | 正在处理中                     |
| delivered    | 成功投递到目标渠道             |
| failed       | 投递失败，已耗尽重试次数       |
| expired      | 消息过期未投递                 |

---

## 4. 通道管理API

### 4.1 创建新通道

**端点**：`POST /api/v1/channels`  

**请求体**：

```json
{
  "type": "email",
  "name": "公司内部邮件通道",
  "config": {
    "smtp_host": "smtp.example.com",
    "smtp_port": 587,
    "username": "noreply@example.com",
    "password": "encrypted_password_here",
    "use_tls": true,
    "rate_limit": 100,
    "rate_period": "minute"
  },
  "enabled": true,
  "tags": ["internal", "notification"]
}
```

**响应**（HTTP 201 Created）：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "channel_id": "ch_20240620XyZ123",
    "type": "email",
    "name": "公司内部邮件通道",
    "status": "active",
    "created_at": "2024-06-20T11:00:00Z"
  }
}
```

### 4.2 获取通道列表

**端点**：`GET /api/v1/channels`  

**查询参数**：

| 参数名 | 类型   | 必需 | 说明                           |
|--------|--------|------|--------------------------------|
| type   | string | 否   | 按渠道类型过滤                 |
| status | string | 否   | 按状态过滤：`active`, `disabled`, `error` |
| page   | int    | 否   | 页码，默认1                    |
| size   | int    | 否   | 每页条数，默认20，最大100      |

**响应**（HTTP 200 OK）：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "total": 5,
    "page": 1,
    "size": 20,
    "items": [
      {
        "channel_id": "ch_20240620XyZ123",
        "type": "email",
        "name": "公司内部邮件通道",
        "status": "active",
        "created_at": "2024-06-20T11:00:00Z",
        "updated_at": "2024-06-20T11:30:00Z"
      },
      {
        "channel_id": "ch_20240620AbC456",
        "type": "sms",
        "name": "阿里云短信通道",
        "status": "active",
        "created_at": "2024-06-19T09:00:00Z",
        "updated_at": "2024-06-20T08:00:00Z"
      }
    ]
  }
}
```

### 4.3 删除通道

**端点**：`DELETE /api/v1/channels/{channel_id}`  

**路径参数**：

| 参数名     | 类型   | 必需 | 说明     |
|------------|--------|------|----------|
| channel_id | string | 是   | 通道ID   |

**响应**（HTTP 200 OK）：

```json
{
  "code": 0,
  "message": "通道已删除",
  "data": {
    "channel_id": "ch_20240620XyZ123",
    "deleted_at": "2024-06-20T12:00:00Z"
  }
}
```

**注意**：删除通道前需确保没有正在处理的消息，否则返回错误码 `4005`。

---

## 5. 消息格式规范（JSON Schema示例）

### 5.1 Email消息格式

**Schema**（email_message.schema.json）：
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "EmailMessage",
  "type": "object",
  "required": ["to", "subject", "body"],
  "properties": {
    "to": {
      "type": "array",
      "items": { "type": "string", "format": "email" },
      "minItems": 1,
      "maxItems": 50,
      "description": "收件人邮箱地址列表"
    },
    "cc": {
      "type": "array",
      "items": { "type": "string", "format": "email" },
      "maxItems": 20,
      "description": "抄送邮箱地址列表"
    },
    "bcc": {
      "type": "array",
      "items": { "type": "string", "format": "email" },
      "maxItems": 20,
      "description": "密送邮箱地址列表"
    },
    "subject": {
      "type": "string",
      "maxLength": 256,
      "description": "邮件主题"
    },
    "body": {
      "type": "object",
      "required": ["content"],
      "properties": {
        "content": { "type": "string", "description": "邮件正文" },
        "content_type": {
          "type": "string",
          "enum": ["text/plain", "text/html"],
          "default": "text/plain"
        }
      }
    },
    "attachments": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["filename", "content_base64"],
        "properties": {
          "filename": { "type": "string", "maxLength": 128 },
          "content_base64": { "type": "string", "description": "Base64编码的文件内容" },
          "mime_type": { "type": "string", "default": "application/octet-stream" }
        }
      },
      "maxItems": 5,
      "description": "附件列表，总大小不超过10MB"
    }
  }
}
```

**示例数据**：
```json
{
  "to": ["user1@example.com", "user2@example.com"],
  "cc": ["manager@example.com"],
  "subject": "系统通知：服务部署完成",
  "body": {
    "content": "<h1>部署成功</h1><p>版本 v2.3.1 已部署到生产环境。</p>",
    "content_type": "text/html"
  }
}
```

### 5.2 SMS消息格式

**Schema**（sms_message.schema.json）：
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "SMSMessage",
  "type": "object",
  "required": ["phone_numbers", "content"],
  "properties": {
    "phone_numbers": {
      "type": "array",
      "items": {
        "type": "string",
        "pattern": "^\\+?[1-9]\\d{6,14}$",
        "description": "国际格式电话号码，如 +8613800138000"
      },
      "minItems": 1,
      "maxItems": 200,
      "description": "接收短信的手机号码列表"
    },
    "content": {
      "type": "string",
      "maxLength": 500,
      "description": "短信内容，中文字符按2个字符计算"
    },
    "signature": {
      "type": "string",
      "maxLength": 10,
      "description": "短信签名，如【公司名称】"
    }
  }
}
```

**示例数据**：
```json
{
  "phone_numbers": ["+8613800138000", "+8613900139000"],
  "content": "您的验证码是：123456，5分钟内有效。",
  "signature": "【云通知】"
}
```

---

## 6. 错误码与异常处理

### 6.1 通用错误码

所有API响应均包含统一的错误结构：

```json
{
  "code": 4001,
  "message": "请求参数校验失败",
  "details": [
    {
      "field": "to",
      "issue": "必须提供至少一个收件人",
      "code": "INVALID_FIELD"
    }
  ],
  "request_id": "req_20240620AbC123"
}
```

### 6.2 错误码列表

| 错误码 | HTTP状态码 | 说明                         | 处理建议                               |
|--------|------------|------------------------------|----------------------------------------|
| 0      | 200/201    | 成功                         | -                                      |
| 4001   | 400        | 请求参数校验失败             | 检查请求体是否符合JSON Schema          |
| 4002   | 400        | 缺少必需头部                 | 确保携带X-API-Key等必需头部            |
| 4003   | 401        | 认证失败（API Key无效）      | 检查API Key是否正确                    |
| 4004   | 401        | 签名验证失败                 | 重新计算签名，检查时间戳是否过期       |
| 4005   | 400        | 通道不存在或已删除           | 检查channel_id是否正确                 |
| 4006   | 400        | 渠道类型不支持               | 使用支持的渠道类型（email, sms等）     |
| 4007   | 429        | 请求频率超过限制             | 降低请求频率，查看X-RateLimit-*头部    |
| 4008   | 413        | 请求体过大（超过1MB）        | 压缩或拆分消息                         |
| 5001   | 500        | 内部服务器错误               | 重试请求，如持续失败请联系技术支持     |
| 5002   | 502        | 下游服务不可用               | 稍后重试，或检查通道配置               |
| 5003   | 503        | 服务暂时过载                 | 使用指数退避策略重试                   |

### 6.3 速率限制

- 每个API Key默认速率：**100次/分钟**。
- 响应头部包含限流信息：
  - `X-RateLimit-Limit`：每分钟允许的请求总数