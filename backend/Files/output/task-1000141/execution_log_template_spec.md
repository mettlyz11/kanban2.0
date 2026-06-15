# execution_log_template_spec

> 任务: v7 #10 执行日志模板化
> 附件类型: 技术规范文档
> 生成时间: 2026-05-12 05:19

# 技术规范文档

**文档编号**：TECH-SPEC-LOG-TPL-v1.0  
**标题**：v7 #10 执行日志模板化  
**编写日期**：2025-04-09  
**作者**：自动化执行系统规范组  
**版本**：1.0  
**状态**：待评审  

---

## 1. 背景与目的

### 1.1 背景

在当前分布式任务执行环境中，各子系统（调度器、执行器、监控服务）均独立产生执行日志。由于缺乏统一的日志结构，导致以下问题：

- **数据碎片化**：不同模块使用不同字段命名（例如 `job_id` vs `taskId`），无法直接关联分析。
- **解析困难**：日志格式从纯文本到非标准JSON混杂，日志采集工具（如ELK栈）需要大量定制解析规则。
- **缺乏一致性**：状态字段使用枚举不统一（如 `success` / `failed` / `FAIL`），聚合统计出错。
- **扩展性差**：新增业务字段需修改全部消费方解析逻辑，变更成本高。

为解决上述问题，需对所有执行日志进行标准化模板化改造，定义统一的字段集、结构约束及语义。

### 1.2 目的

本规范旨在：

- 统一执行日志的字段定义、数据类型与约束，确保跨系统互操作。
- 提供标准JSON Schema，作为日志生产与消费的契约。
- 降低日志集成、监控告警与审计追溯的复杂度。
- 明确接入方式与适配要求，支持快速迁移。

### 1.3 适用范围

本规范适用于所有参与任务执行、调度的微服务及工具，包括但不限于：

- 任务调度中心（Scheduler）
- 工作节点执行器（Worker/Executor）
- 健康检查与重试服务
- 命令行客户端输出的结构化日志

---

## 2. 日志字段定义

### 2.1 总览

执行日志采用JSON对象表示，每条日志记录一个任务执行生命周期中的一次事件。下表定义所有标准字段。

| 字段名 | 类型 | 必填 | 说明 |
|--------|------|------|------|
| `task_id` | string | 是 | 全局唯一任务标识。通常由调度器生成，遵循UUID v4格式（如`a1b2c3d4-e5f6-7890-abcd-ef1234567890`）。 |
| `status` | string | 是 | 当前事件对应的执行状态。枚举值，参见2.2节。 |
| `timestamp` | string | 是 | 事件发生的精确时间。格式为ISO 8601 UTC，例如`2025-04-09T12:34:56.789Z`，精度到毫秒。 |
| `message` | string | 是 | 人类可读的事件描述。应简明扼要，包含核心上下文。长度限制2000字符（UTF-8编码）。 |
| `source` | string | 是 | 产生日志的模块标识。使用点分命名法，如`worker.executor`、`scheduler.dispatch`。长度不超过128字符。 |
| `duration` | integer | 否 | 本次执行阶段的耗时（毫秒）。例如任务执行耗时、重试等待时间。无则省略或填0。 |
| `attempt` | integer | 否 | 当前重试次数（从1开始计数）。仅首次执行或非重试任务时可省略。 |
| `owner` | string | 否 | 任务所有者/创建者的标识符（如用户ID或租户ID）。用于多租户场景过滤。 |
| `context` | object | 否 | 扩展上下文，用于携带非标准化附加信息。内部字段以`x_`开头，避免与标准字段冲突。 |
| `error_code` | string | 条件必填 | 当`status`为`failed`或`error`时必须提供。建议使用业务错误码（如`E_TIMEOUT`、`E_RESOURCE_EXHAUSTED`），长度不超过64字符。 |
| `error_detail` | string | 否 | 错误的详细信息，包括堆栈或原因。不可包含敏感凭据。长度不超过4000字符。 |
| `correlation_id` | string | 否 | 用于跨服务追踪的请求流水号。如果在分布式上下文中，应与上层调用链的ID一致。 |

### 2.2 状态枚举（`status`字段）

| 值 | 含义 | 典型场景 |
|----|------|----------|
| `queued` | 任务已进入等待队列 | 调度器将任务提交到队列后立即记录 |
| `assigned` | 任务已被分配给具体执行节点 | 调度器确定worker后记录 |
| `running` | 执行器开始处理任务 | worker开始执行业务逻辑前记录 |
| `progress` | 任务执行中阶段性事件 | 长任务定期报告进度（可能包含进度百分比到`message`中） |
| `completed` | 任务成功完成 | 任务返回成功结果后记录 |
| `failed` | 任务执行失败（非临时性） | 业务逻辑异常、无可用重试次数后记录 |
| `error` | 系统级错误（如网络、资源） | worker进程崩溃前捕获异常记录 |
| `retrying` | 任务即将重试 | 在重试策略触发前记录，`attempt`字段表示当前次数 |
| `cancelled` | 任务被取消 | 用户手动或超时策略取消任务 |
| `timeout` | 任务超时 | 超出任务最大执行时间 |

### 2.3 字段详细说明

- **task_id**：长度36~64字符，建议UUID。若系统使用其他唯一标识（如雪花ID），应转换为不带连字符的字符串，并保持全局唯一。
- **timestamp**：必须为UTC时间，不允许含时区偏移。建议由采集系统统一转换为UTC，源系统直接输出UTC。
- **message**：需使用模板化文本，例如`"Task a1b2c3d4 executed in 1234ms"`。避免包含非结构化大段文本。
- **context**：示例：`{"x_retry_policy": "exponential", "x_node_version": "1.2.3"}`。不允许包含`task_id`、`status`等已在标准字段定义的键。
- **error_code**与**error_detail**：生产者必须确保不因日志记录抛出异常。如果`error_detail`包含敏感信息，应在输出前脱敏。

---

## 3. JSON Schema定义

以下JSON Schema描述日志模板的完整结构，用于生产消费双方的契约验证。该Schema遵循Draft 2020-12规范。

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://example.com/schemas/execution-log-v1.json",
  "title": "Execution Log Template",
  "description": "Standard schema for task execution log entries across the system.",
  "type": "object",
  "required": [
    "task_id",
    "status",
    "timestamp",
    "message",
    "source"
  ],
  "properties": {
    "task_id": {
      "type": "string",
      "pattern": "^[a-f0-9]{8}-?[a-f0-9]{4}-?[a-f0-9]{4}-?[a-f0-9]{4}-?[a-f0-9]{12}$",
      "description": "Globally unique task identifier, preferably UUID v4."
    },
    "status": {
      "type": "string",
      "enum": [
        "queued",
        "assigned",
        "running",
        "progress",
        "completed",
        "failed",
        "error",
        "retrying",
        "cancelled",
        "timeout"
      ],
      "description": "Execution status at the time of the log event."
    },
    "timestamp": {
      "type": "string",
      "format": "date-time",
      "pattern": "^\\d{4}-\\d{2}-\\d{2}T\\d{2}:\\d{2}:\\d{2}\\.\\d{3}Z$",
      "description": "ISO 8601 UTC timestamp with millisecond precision."
    },
    "message": {
      "type": "string",
      "maxLength": 2000,
      "description": "Human-readable description of the event."
    },
    "source": {
      "type": "string",
      "maxLength": 128,
      "pattern": "^[a-z]+(\\.[a-z0-9_]+)*$",
      "description": "Dot-separated module identifier, e.g., worker.executor."
    },
    "duration": {
      "type": "integer",
      "minimum": 0,
      "exclusiveMinimum": 0,
      "description": "Elapsed time in milliseconds for the stage represented by this log."
    },
    "attempt": {
      "type": "integer",
      "minimum": 1,
      "description": "Retry attempt number (1-based)."
    },
    "owner": {
      "type": "string",
      "maxLength": 64,
      "description": "Identifier of the task owner, e.g., user ID."
    },
    "context": {
      "type": "object",
      "maxProperties": 20,
      "propertyNames": {
        "pattern": "^x_[a-zA-Z0-9_]+$"
      },
      "additionalProperties": {
        "type": "string"
      },
      "description": "Extension context object. All keys must start with 'x_'."
    },
    "error_code": {
      "type": "string",
      "maxLength": 64,
      "description": "Business error code, required if status is 'failed' or 'error'."
    },
    "error_detail": {
      "type": "string",
      "maxLength": 4000,
      "description": "Detailed error information, may include stack trace (sensitive data should be redacted)."
    },
    "correlation_id": {
      "type": "string",
      "maxLength": 128,
      "description": "Correlation ID for distributed tracing."
    }
  },
  "allOf": [
    {
      "if": {
        "properties": { "status": { "enum": ["failed", "error"] } }
      },
      "then": {
        "required": ["error_code"]
      }
    }
  ]
}
```

**Schema说明**：
- 使用`pattern`对`task_id`进行UUID格式校验（支持有无连字符两种形式），若实际使用非UUID，应调整正则。
- `timestamp`格式强制为ISO 8601且末尾带`Z`，`format: date-time`提供基础校验，`pattern`进一步要求毫秒精度。
- `source`使用小写点分命名，允许字母开头，后续含字母、数字、下划线。
- `context`对象限制最多20个字段，且键必须以`x_`开头，值限定为字符串（可放宽为允许基本类型，此处为保持简单）。
- 条件必填：当status为`failed`或`error`时，`error_code`字段变为必需。

---

## 4. 示例

### 4.1 正常执行日志示例（成功）

```json
{
  "task_id": "b2c3d4e5-f6a7-8901-bcde-f12345678901",
  "status": "completed",
  "timestamp": "2025-04-09T14:30:10.123Z",
  "message": "Task processed successfully in 2456ms",
  "source": "worker.executor",
  "duration": 2456,
  "attempt": 1,
  "owner": "tenant-a",
  "context": {
    "x_region": "us-east-1",
    "x_worker_version": "2.3.1"
  },
  "correlation_id": "trace-abc123"
}
```

### 4.2 失败日志示例（含错误信息）

```json
{
  "task_id": "f1a2b3c4-d5e6-7890-abcd-ef1234567890",
  "status": "failed",
  "timestamp": "2025-04-09T14:35:22.987Z",
  "message": "Task failed due to database connection timeout",
  "source": "worker.executor",
  "duration": 5012,
  "attempt": 2,
  "owner": "tenant-b",
  "error_code": "E_DB_TIMEOUT",
  "error_detail": "TimeoutException: Connection to database 'prod-db' timed out after 5000ms\n    at com.example.DbClient.connect(DbClient.java:45)\n    at com.example.TaskRunner.run(TaskRunner.java:120)",
  "context": {
    "x_retry_count": 2,
    "x_max_retries": 3
  },
  "correlation_id": "trace-def456"
}
```

### 4.3 重试日志示例

```json
{
  "task_id": "c3d4e5f6-a7b8-9012-cdef-123456789abc",
  "status": "retrying",
  "timestamp": "2025-04-09T14:40:00.500Z",
  "message": "Scheduling retry attempt 2/3 in 10s",
  "source": "scheduler.retry",
  "attempt": 2,
  "owner": "tenant-a",
  "duration": 10000,
  "context": {
    "x_previous_error": "E_NETWORK"
  }
}
```

### 4.4 进度日志示例（长任务中间状态）

```json
{
  "task_id": "d4e5f6a7-b8c9-0123-defa-456789abcdef",
  "status": "progress",
  "timestamp": "2025-04-09T15:00:15.000Z",
  "message": "Processing batch 7 of 20 (35% complete)",
  "source": "worker.executor",
  "attempt": 1,
  "owner": "tenant-c",
  "context": {
    "x_progress_percent": 35,
    "x_current_batch": 7,
    "x_total_batches": 20
  }
}
```

---

## 5. 接入建议

### 5.1 总体原则

- **渐进式迁移**：现有系统可以先在关键路径（如调度器、worker）按新模板输出日志，同时保留旧日志一段时间，待消费方完成适配后切换。
- **字段映射**：将当前日志中已有字段按下表映射到标准字段。映射不丢失信息，且保持语义一致。

### 5.2 字段映射表

| 常见旧字段名 | 映射到标准字段 | 转换逻辑 |
|------------|--------------|----------|
| `job_id`、`request_id` | `task_id` | 保持原值，若格式不符合UUID，保留但需全局唯一 |
| `state`、`event_type` | `status` | 按状态枚举转换表 |
| `time`、`log_time` | `timestamp` | 转换为ISO 8601 UTC字符串，精度到毫秒 |
| `msg`、`desc` | `message` | 取前2000字符，去除敏感信息 |
| `module`、`component` | `source` | 转换为点分命名 |
| `elapsed_ms` | `duration` | 直接映射，若为秒则乘以1000 |
| `retry_count` | `attempt` | 如果从0开始计数，则+1；若已有则直接映射 |
| `user_id`、`tenant` | `owner` | 统一为字符串标识 |
| `error`、`exception` | `error_detail` | 只保留1000字符内的堆栈，脱敏密码/密钥 |
| `error_code` | `error_code` | 统一转换为大写带前缀（如`E_`），无编码时生成`E_UNKNOWN` |
| `trace_id` | `correlation_id` | 原值直接映射 |

### 5.3 状态转换映射

假设旧系统使用如下状态值，按表转换：

| 旧状态值 | 新状态值 |
|---------|---------|
| `pending` / `waiting` | `queued` |
| `allocated` | `assigned` |
| `processing` / `active` | `running` |
| `progress` / `in_progress` | `progress` |
| `success` / `ok` | `completed` |
| `fail` / `failure` | `failed` |
| `system_error` | `error` |
| `retrying` | `retrying` |
| `cancel` / `aborted` | `cancelled` |
| `timeout` | `timeout` |

### 5.4 代码接入示例（Python）

```python
import json
import uuid
from datetime import