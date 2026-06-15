# ResourceDashboardAPI

> 任务: v8 #13 系统资源看板 — CPU/内存/DB连接数
> 附件类型: API文档
> 生成时间: 2026-05-12 06:25

# 系统资源看板 — 数据接口规范 V1.0

**文档状态：** 正式发布  
**版本号：** 1.0  
**最后更新：** 2025-07-15  
**适用系统：** v8 #13 系统资源看板  

---

## 1. 文档概述

本文档定义了系统资源看板（v8 #13）所需的数据接口规范，涵盖以下两类通信方式：

- **RESTful API**：用于获取实时快照及历史趋势数据，支持客户端主动请求。
- **WebSocket 实时推送**：用于服务端主动向看板推送资源指标的实时变化，保证前端展示的低延迟。

所有接口数据均以 **JSON** 格式交互，编码统一使用 **UTF-8**。本文档是前后端团队在对接过程中的唯一参考依据，任何接口变更均需通过版本管理流程同步。

---

## 2. API 端点列表与说明

| 序号 | 端点                        | 方法 | 功能描述               | 认证要求 |
|------|-----------------------------|------|------------------------|----------|
| 1    | `/api/resources/current`   | GET  | 获取当前资源使用快照   | Bearer Token |
| 2    | `/api/resources/history`   | GET  | 获取指定时间范围内的历史数据 | Bearer Token |
| 3    | `/ws/resources`            | WS   | 实时推送资源指标       | 无需单独认证（基于连接身份） |

所有 RESTful 请求需在 `Authorization` 头中携带 `Bearer <token>`，Token 由统一认证中心下发。

---

## 3. GET /api/resources/current — 当前资源快照

### 3.1 请求方法与路径

**HTTP 方法：** `GET`  
**URL 路径：** `/api/resources/current`  
**无查询参数，** 返回当前时刻服务器资源的瞬时值。

### 3.2 响应格式

**HTTP 状态码：** `200 OK`  
**Content-Type：** `application/json; charset=utf-8`

响应体为 JSON 对象，包含三个顶级字段：

```json
{
  "status": "success",
  "timestamp": 1721049600,
  "data": {
    "cpu": {
      "usage_percent": 45.3,
      "load_1m": 2.1,
      "load_5m": 1.8,
      "load_15m": 1.5,
      "cores": 8
    },
    "memory": {
      "total_mb": 32768,
      "used_mb": 18432,
      "free_mb": 14336,
      "usage_percent": 56.2,
      "swap_used_mb": 2048,
      "swap_total_mb": 4096
    },
    "database": {
      "total_connections": 200,
      "active_connections": 42,
      "idle_connections": 15,
      "max_connections": 300,
      "connection_usage_percent": 28.5
    }
  }
}
```

### 3.3 字段说明

| 字段路径                        | 类型    | 单位/范围           | 说明                          |
|---------------------------------|---------|----------------------|-------------------------------|
| `status`                        | string  | "success"/"error"    | 请求处理结果                   |
| `timestamp`                     | int64   | 秒级 Unix 时间戳     | 数据采集时刻                   |
| `data.cpu.usage_percent`        | float   | 0.0 ~ 100.0          | CPU 总体使用率（加权平均）     |
| `data.cpu.load_1m`             | float   | ≥0                  | 1 分钟平均负载                 |
| `data.cpu.load_5m`             | float   | ≥0                  | 5 分钟平均负载                 |
| `data.cpu.load_15m`            | float   | ≥0                  | 15 分钟平均负载                |
| `data.cpu.cores`               | int     | ≥1                  | CPU 逻辑核心数                 |
| `data.memory.total_mb`         | int     | MB                  | 物理内存总量                   |
| `data.memory.used_mb`          | int     | MB                  | 已使用的物理内存               |
| `data.memory.free_mb`          | int     | MB                  | 空闲物理内存                   |
| `data.memory.usage_percent`    | float   | 0.0 ~ 100.0          | 内存使用率（含缓存/缓冲区）    |
| `data.memory.swap_used_mb`     | int     | MB                  | 已用交换空间                   |
| `data.memory.swap_total_mb`    | int     | MB                  | 交换空间总量                   |
| `data.database.total_connections` | int   | 个数                | 当前数据库总连接数             |
| `data.database.active_connections` | int | 个数                | 活跃连接数                     |
| `data.database.idle_connections`  | int   | 个数                | 空闲连接数                     |
| `data.database.max_connections`   | int   | 个数                | 数据库最大连接数配置值         |
| `data.database.connection_usage_percent` | float | 0.0 ~ 100.0 | 连接使用率 = total / max * 100 |

### 3.4 错误响应示例

```json
{
  "status": "error",
  "code": 401,
  "message": "未授权，请提供有效的 Bearer Token"
}
```

所有错误均采用标准 HTTP 状态码，详见第 6 节。

---

## 4. GET /api/resources/history — 历史数据接口

### 4.1 请求方法、参数与路径

**HTTP 方法：** `GET`  
**URL 路径：** `/api/resources/history`

**查询参数说明：**

| 参数名      | 类型   | 必须 | 默认值 | 说明                                      |
|-------------|--------|------|--------|-------------------------------------------|
| `start_time` | int64  | 是   | -      | 起始 Unix 时间戳（秒级）                  |
| `end_time`   | int64  | 是   | -      | 结束 Unix 时间戳（秒级），必须大于 start_time |
| `metric`     | string | 否   | "all"  | 资源类型：`cpu` / `memory` / `database` / `all` |
| `interval`   | string | 否   | "1m"   | 数据聚合间隔：`1m` / `5m` / `15m` / `1h`   |

**示例请求：**  
`GET /api/resources/history?start_time=1721046000&end_time=1721049600&metric=cpu&interval=5m`

### 4.2 响应格式

```json
{
  "status": "success",
  "query": {
    "start_time": 1721046000,
    "end_time": 1721049600,
    "metric": "cpu",
    "interval": "5m"
  },
  "data": {
    "cpu": [
      {
        "timestamp": 1721046300,
        "usage_percent": 42.1,
        "load_1m": 1.9,
        "load_5m": 1.7,
        "load_15m": 1.4
      },
      {
        "timestamp": 1721046600,
        "usage_percent": 44.8,
        "load_1m": 2.0,
        "load_5m": 1.8,
        "load_15m": 1.5
      }
    ],
    "memory": [],
    "database": []
  }
}
```

当 `metric=all` 时，`data` 包含三个子数组，每个子数组内为对应时间序列。  
每个时间点的数据字段与 `/current` 中 `data` 对应部分的字段一致，但数量可能因 `interval` 聚合而减少。

### 4.3 聚合说明

- `interval=1m`：返回原始采样点（60 秒一个点），最多返回 1440 点（24 小时）。
- `interval=5m`：每 5 分钟取平均值，包含 5 分钟内所有采样点的均值。
- `interval=15m` / `1h`：类似地取时间窗口内的平均值。

注意：历史数据最长可查询 7 天前，通过 `interval=1h` 可支持 7 * 24 = 168 个数据点。

### 4.4 错误响应

```json
{
  "status": "error",
  "code": 400,
  "message": "参数 `start_time` 或 `end_time` 缺失或无效"
}
```

---

## 5. WebSocket /ws/resources — 实时推送协议

### 5.1 连接建立

客户端通过 `wss://<host>/ws/resources` 建立 WebSocket 连接。无需额外参数，但连接的合法性由底层网关根据 Cookie 或 Token 验证（实现方式由网关层决定，此文档不涉及）。

### 5.2 消息格式（服务端 → 客户端）

服务端推送的消息均为 JSON 格式，包含以下顶层结构：

```json
{
  "type": "resource_update",
  "timestamp": 1721049601,
  "data": {
    "cpu": { /* 与 /current 中 cpu 结构相同 */ },
    "memory": { /* 与 /current 中 memory 结构相同 */ },
    "database": { /* 与 /current 中 database 结构相同 */ }
  }
}
```

**字段说明：**
- `type`：固定为 `"resource_update"`，客户端可根据此字段区分不同消息类型（未来可扩展）。
- `timestamp`：服务端采集时刻的 Unix 时间戳（秒级），精度为秒。
- `data`：当前时刻的资源指标全量快照，结构与 `/current` 的 `data` 完全一致。

### 5.3 推送频率

- **正常模式**：每 5 秒推送一次。
- **拥塞控制**：若服务端检测到 CPU 或内存使用率超过 90%，推送频率自动降至每 15 秒一次，并在 `data` 中附加 `"throttled": true` 字段（位于 `data` 顶层）。当指标回落后恢复 5 秒间隔。

```json
{
  "type": "resource_update",
  "timestamp": 1721049700,
  "data": {
    "cpu": { ... },
    "memory": { ... },
    "database": { ... },
    "throttled": true
  }
}
```

### 5.4 心跳保持

服务端每 30 秒发送一条心跳消息：

```json
{
  "type": "heartbeat"
}
```

客户端无需应答，但若连续 3 个心跳（90 秒）未收到任何消息，客户端应主动断开并重连。

### 5.5 客户端消息（可选）

客户端可向服务端发送以下消息（JSON 格式）：

- **订阅指标类型**：`{"type": "subscribe", "metrics": ["cpu", "database"]}`  
  服务端收到后仅推送指定指标的数据，其他指标省略，以减少带宽。默认推送全部三个指标。
- **取消订阅**：`{"type": "unsubscribe", "metrics": ["memory"]}`  
  动态减少推送字段。

### 5.6 连接关闭

服务端会在以下情况主动关闭连接并返回关闭码：

- 身份验证失败：关闭码 4001
- 客户端发送非法 JSON：关闭码 4002
- 服务器即将重启：关闭码 1012，并附文字 `"Server shutdown"`

客户端应实现重连逻辑，间隔从 1 秒开始，指数退避至 30 秒上限。

---

## 6. 错误码与异常处理规范

### 6.1 RESTful API 错误码

| HTTP 状态码 | 错误码（body 中的 code） | 说明                    | 常见场景                              |
|-------------|--------------------------|-------------------------|---------------------------------------|
| 400         | 400                      | 请求参数错误            | 缺少必填参数、参数格式错误             |
| 401         | 401                      | 未授权                  | Token 缺失、过期或无效                 |
| 403         | 403                      | 禁止访问                | Token 有效但无此数据权限               |
| 404         | 404                      | 端点不存在              | 路径拼写错误                           |
| 429         | 429                      | 请求频率过高            | 超过 10 次/秒 的限制（见速率限制）     |
| 500         | 500                      | 服务端内部错误          | 数据库异常、采集器崩溃                 |
| 503         | 503                      | 服务暂不可用            | 系统正在重启或过载                     |

所有错误响应均包含 `status: "error"`、`code` 和 `message` 字段。`message` 可能为中文或英文，推荐前端根据 `code` 展示统一文案。

### 6.2 WebSocket 错误

- 连接阶段失败：HTTP 升级时返回 401 或 403，WebSocket 连接不会建立。
- 连接后错误：通过关闭帧传递错误码（如 4001, 4002），客户端应解析关闭码并采取相应动作。
- 数据推送异常：若服务端内部采集失败，推送中对应指标字段值为 `null`。

### 6.3 速率限制

- RESTful API：每客户端每秒最多 10 次请求（由 `X-RateLimit-Remaining` 头指示）。超限后返回 429。
- WebSocket：无速率限制，但客户端应避免过于频繁的订阅/取消订阅操作（建议间隔 > 1 秒）。

---

## 7. 模拟数据与真实数据切换配置说明

### 7.1 目的

在开发、测试及演示环境中，后端可配置为返回模拟数据，避免依赖真实服务器状态；生产环境必须为真实数据。

### 7.2 配置方式

通过环境变量或配置文件 `config.yaml` 控制，推荐使用环境变量：

```yaml
# config.yaml 片段
resource_monitor:
  mode: "mock"          # 可选 "mock" 或 "real"
  mock_data_file: "data/mock_resources.json"   # 模拟数据模板路径
  real_data_source: "prometheus"                # 真实数据源（如 Prometheus）
```

环境变量优先级高于配置文件：`MONITOR_MODE=mock` 将覆盖配置。

### 7.3 模拟数据文件格式

`mock_data_file` 指定一个 JSON 文件，内容结构与 `/current` 的 `data` 字段一致，但服务端会对其中的值在一定范围内添加随机扰动（±5%）以模拟实时变化。

示例 `mock_resources.json`：

```json
{
  "cpu": {
    "usage_percent": 50.0,
    "load_1m": 2.0,
    "load_5m": 1.7,
    "load_15m": 1.4,
    "cores": 8
  },
  "memory": {
    "total_mb": 32768,
    "used_mb": 16000,
    "free_mb": 16768,
    "usage_percent": 48.83,
    "swap_used_mb": 1000,
    "swap_total_mb": 4096
  },
  "database": {
    "total_connections": 150,
    "active_connections": 30,
    "idle_connections": 20,
    "max_connections": 300,
    "connection_usage_percent": 50.0
  }
}
```

### 7.4 切换影响

- **RESTful API**：`/current` 和 `/history` 返回模拟数据；`/history` 中，若 `interval=1m`，服务端生成过去 1 小时的模拟时间序列（基于模板加噪声）。
- **WebSocket**：推送频率仍为 5 秒，但数据来自对模拟模板的实时微调。
- **安全**：模拟模式下，所有接口仍要求有效 Token，但可配置一个固定测试 Token 以简化开发 (例如 `test-token-123`)。

### 7.5 真实数据源对接

当 `mode: "real"` 时，后端从指定数据源（如 Prometheus、数据库连接池监控）采集指标。各指标对应的 PromQL 查询示例如下（供运维部署参考）：

| 指标                  | PromQL 查询表达式                                                                 |
|-----------------------|----------------------------------------------------------------------------------|
| CPU usage_percent     | `100 - (avg by (instance) (rate(node_cpu_seconds_total{mode="idle"}[1m])) * 100)` |
| Memory usage_percent  | `(1 - (node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes)) * 100`       |
| DB active_connections | `pg