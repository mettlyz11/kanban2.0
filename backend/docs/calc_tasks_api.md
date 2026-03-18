# 计算任务提交 API 文档

## 概述

T109 功能 - 计算任务提交和管理 API，用于将量子化学计算任务提交到处理队列。

## 基础信息

- **Base URL**: `http://localhost:5001/api`
- **数据格式**: JSON
- **认证**: 当前无需认证（生产环境需添加）

---

## API 端点

### 1. 提交计算任务

**端点**: `POST /api/calc-tasks/submit`

**描述**: 提交新的计算任务到队列

**请求参数**:

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| reaction_id | integer | ✅ | 反应 ID |
| task_type | string | ✅ | 任务类型：optimization/ts/frequency/single_point/irc |
| software | string | ❌ | 计算软件：Gaussian/ORCA/Psi4/NWChem |
| input_data | object/string | ✅ | 输入数据（JSON 对象或文件内容/路径） |

**请求示例**:

```bash
curl -X POST http://localhost:5001/api/calc-tasks/submit \
  -H "Content-Type: application/json" \
  -d '{
    "reaction_id": 1,
    "task_type": "optimization",
    "software": "Gaussian",
    "input_data": {
      "method": "B3LYP",
      "basis": "6-31G(d)",
      "molecule": "H2O\nO 0.0 0.0 0.0\nH 0.0 0.757 0.586\nH 0.0 -0.757 0.586"
    }
  }'
```

**成功响应** (201):

```json
{
  "success": true,
  "message": "计算任务已成功提交到队列",
  "task": {
    "task_id": 123,
    "reaction_id": 1,
    "task_type": "optimization",
    "software": "Gaussian",
    "status": "queued",
    "created_at": "2026-03-11T23:30:00",
    "queue_position": "pending"
  }
}
```

**错误响应** (400):

```json
{
  "success": false,
  "error": "validation_error",
  "message": "缺少必需字段：task_type, input_data",
  "missing_fields": ["task_type", "input_data"]
}
```

**错误响应** (500):

```json
{
  "success": false,
  "error": "internal_error",
  "message": "服务器内部错误：数据库连接失败"
}
```

---

### 2. 获取任务详情

**端点**: `GET /api/calc-tasks/<task_id>`

**描述**: 获取指定任务的详细信息

**路径参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| task_id | integer | 任务 ID |

**请求示例**:

```bash
curl http://localhost:5001/api/calc-tasks/123
```

**成功响应** (200):

```json
{
  "success": true,
  "task": {
    "id": 123,
    "reaction_id": 1,
    "task_type": "optimization",
    "software": "Gaussian",
    "status": "running",
    "input_file": "/path/to/input.com",
    "result_data": "{\"energy\": -76.123456}",
    "created_at": "2026-03-11T23:30:00",
    "started_at": "2026-03-11T23:31:00",
    "completed_at": null,
    "input_content": "%chk=opt.chk\n#P B3LYP/6-31G(d) Opt\n...",
    "result_json": {
      "energy": -76.123456
    }
  }
}
```

**错误响应** (404):

```json
{
  "success": false,
  "error": "not_found",
  "message": "任务 999 不存在"
}
```

---

### 3. 获取任务列表

**端点**: `PUT /api/calc-tasks`

**描述**: 获取计算任务列表（支持分页和过滤）

**查询参数**:

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| page | integer | 1 | 页码 |
| per_page | integer | 20 | 每页数量 |
| status | string | - | 状态过滤：queued/running/completed/failed |
| reaction_id | integer | - | 反应 ID 过滤 |

**请求示例**:

```bash
# 获取所有任务
curl "http://localhost:5001/api/calc-tasks"

# 获取第 2 页，每页 50 个
curl "http://localhost:5001/api/calc-tasks?page=2&per_page=50"

# 过滤运行中的任务
curl "http://localhost:5001/api/calc-tasks?status=running"

# 过滤特定反应的任务
curl "http://localhost:5001/api/calc-tasks?reaction_id=1"
```

**成功响应** (200):

```json
{
  "success": true,
  "tasks": [
    {
      "id": 123,
      "reaction_id": 1,
      "task_type": "optimization",
      "software": "Gaussian",
      "status": "queued",
      "created_at": "2026-03-11T23:30:00"
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 1,
    "pages": 1
  }
}
```

---

### 4. 获取任务统计

**端点**: `GET /api/calc-tasks/stats`

**描述**: 获取计算任务的统计数据

**请求示例**:

```bash
curl http://localhost:5001/api/calc-tasks/stats
```

**成功响应** (200):

```json
{
  "success": true,
  "stats": {
    "total": 150,
    "running": 3,
    "completed": 142,
    "failed": 5
  }
}
```

---

## 任务类型说明

| 类型 | 说明 | 用途 |
|------|------|------|
| optimization | 几何优化 | 寻找分子稳定构型 |
| ts | 过渡态搜索 | 寻找反应过渡态 |
| frequency | 频率计算 | 验证优化结果，计算热力学校正 |
| single_point | 单点能计算 | 在指定构型下计算能量 |
| irc | 内禀反应坐标 | 验证过渡态连接的反应物和产物 |

---

## 支持的软件

| 软件 | 说明 |
|------|------|
| Gaussian | 通用量子化学软件 |
| ORCA | 免费高效的量子化学软件 |
| Psi4 | 开源量子化学软件 |
| NWChem | 高性能计算化学软件 |

---

## 任务状态

| 状态 | 说明 |
|------|------|
| queued | 已提交，等待处理 |
| running | 正在计算 |
| completed | 计算完成 |
| failed | 计算失败 |

---

## 错误代码

| HTTP 状态码 | 错误类型 | 说明 |
|------------|---------|------|
| 200 | success | 请求成功 |
| 201 | created | 任务创建成功 |
| 400 | validation_error | 请求参数验证失败 |
| 404 | not_found | 资源不存在 |
| 500 | internal_error | 服务器内部错误 |

---

## 测试

运行测试脚本：

```bash
cd /Users/mettlyz/.openclaw/workspace/kanban-react/backend
python3 test_calc_tasks_api.py
```

---

## 日志

计算任务相关日志记录在应用日志中，使用 logger 名称 `calc_tasks`。

**日志级别**:
- INFO: 任务提交成功
- WARNING: 验证失败、非关键问题
- ERROR: 异常、数据库错误

---

## 数据库表结构

```sql
CREATE TABLE calc_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reaction_id INTEGER NOT NULL,
    task_type TEXT NOT NULL,
    software TEXT,
    input_file TEXT,
    status TEXT DEFAULT 'queued',
    result_data TEXT,
    created_at DATETIME,
    started_at DATETIME,
    completed_at DATETIME,
    error_message TEXT
);
```

---

## 更新日志

- **2026-03-11**: 初始版本，实现任务提交、查询、列表、统计功能
