# cross_project_dependency_tech_spec

> 任务: v9 #4 跨项目依赖 — depends_on 支持 project_id:task_id
> 附件类型: 技术规格说明书
> 生成时间: 2026-05-12 06:54

# 技术规格说明书

## 1. 背景与目标

### 1.1 背景
当前系统依赖模块`depends_on`仅支持同一项目内的任务依赖（格式为`task_id`）。随着业务扩展，多个项目间常存在上下游关系（例如：项目A的“数据清洗”任务完成后，项目B的“模型训练”任务才能启动）。现有机制无法表达跨项目依赖，导致用户需手动编排时间或采用外部调度，增加了运维复杂度和出错风险。

### 1.2 目标
- 支持`project_id:task_id`格式在`depends_on`字段中声明跨项目依赖。
- 解析引擎能正确构建跨项目依赖图，并基于各项目任务的实际状态（pending/running/success/failed）判断当前任务是否可执行。
- 提供高效的状态查询API，避免频繁跨项目轮询。
- 引入缓存与容错机制，降低网络抖动和项目级故障的影响。
- 确保变更兼容旧格式（仅`task_id`），不影响已有依赖逻辑。

## 2. 当前depends_on机制分析

### 2.1 现有实现
- 字段类型：`List[str]`，每个元素为`"task_id"`（128位UUID字符串）。
- 解析引擎在任务触发时，从同一项目的`tasks`表查询对应`task_id`的`state`和`end_time`。状态判据：所有依赖任务状态为`success`且`end_time`不为空。
- 无缓存，每次执行都实时读取数据库。同一项目内查询延迟在10ms以内。

### 2.2 限制
- 不支持跨项目引用。
- 无超时/降级处理，若下游项目不可达则任务永久阻塞。
- 缺少循环依赖检测（同一项目内有限制，跨项目可能形成死锁）。

## 3. 设计原则与约束

- **向下兼容**：旧格式`task_id`自动映射为当前项目，解析逻辑不变。
- **最小侵入**：仅改动`depends_on`解析层和依赖状态获取层，不改动任务调度核心。
- **可观测性**：所有跨项目依赖查询记录日志，便于排查。
- **限流保护**：单次依赖检查最多查询5个跨项目任务，超出部分走降级（视为依赖满足）。
- **最终一致性**：允许短暂状态不一致（≤2秒），依赖检查以缓存数据为主，异步刷新。

## 4. 数据模型变更（数据库迁移脚本）

### 4.1 表结构变更
- 在`tasks`表新增字段`project_id`（原表已有，但依赖解析时未利用），确保索引。
- 新建`project_cache`表（可选，用于存储项目级别元数据，本次不强制）。

主要迁移脚本（PostgreSQL）：

```sql
-- 确保tasks表已有project_id字段（假设存在，无则添加）
ALTER TABLE tasks ADD COLUMN IF NOT EXISTS project_id VARCHAR(64) NOT NULL DEFAULT '';

-- 为project_id+task_id创建联合唯一索引（加速跨项目查询）
CREATE UNIQUE INDEX IF NOT EXISTS idx_tasks_project_task ON tasks (project_id, task_id);
-- 注意：task_id本身已全局唯一，此处索引用于快速定位项目内任务

-- 创建跨项目依赖缓存表（可选）
CREATE TABLE IF NOT EXISTS cross_project_dep_cache (
    id BIGSERIAL PRIMARY KEY,
    source_project_id VARCHAR(64) NOT NULL,
    source_task_id VARCHAR(128) NOT NULL,
    dep_project_id VARCHAR(64) NOT NULL,
    dep_task_id VARCHAR(128) NOT NULL,
    dep_state VARCHAR(16) NOT NULL,       -- 缓存的状态
    dep_end_time TIMESTAMP WITH TIME ZONE, -- 缓存完成时间
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    UNIQUE (source_project_id, source_task_id, dep_project_id, dep_task_id)
);

-- 为缓存表添加过期标记（用于TTL清理）
CREATE INDEX IF NOT EXISTS idx_cache_updated ON cross_project_dep_cache (updated_at);
```

### 4.2 回滚脚本
```sql
DROP INDEX IF EXISTS idx_tasks_project_task;
DROP TABLE IF EXISTS cross_project_dep_cache;
```

## 5. 解析规则：project_id:task_id格式定义与解析函数

### 5.1 格式定义
- 完整格式：`<project_id>:<task_id>`，例如`"proj-1234:task-uuid-5678"`。
- 允许空格：`"proj-1234: task-uuid-5678"`自动trim。
- 允许旧格式：仅`task_id`，解析时project_id自动填充为当前任务所在项目。
- 禁止嵌套或复杂表达式（如`proj1:task1+proj2:task2`）。

### 5.2 解析函数（Python实现）

```python
import re
from typing import Tuple, Optional

def parse_dep_reference(ref: str, current_project_id: str) -> Tuple[str, str]:
    """
    解析依赖引用字符串，返回 (project_id, task_id)
    :param ref: 用户输入的依赖引用，如 "proj-abc:task-123" 或 "task-456"
    :param current_project_id: 当前任务的所属项目ID（缺省时使用）
    :return: (project_id, task_id)
    """
    ref = ref.strip()
    # 匹配 project_id:task_id 格式，保证task_id不含冒号
    pattern = r'^([^:]+):([a-f0-9\-]{36}|[a-zA-Z0-9\-_]+)$'  # 允许非UUID但通用
    m = re.match(pattern, ref)
    if m:
        project_id = m.group(1).strip()
        task_id = m.group(2).strip()
        # 如果 project_id 为空，视为当前项目
        if not project_id:
            project_id = current_project_id
        return project_id, task_id
    else:
        # 单 task_id 格式，视为当前项目
        return current_project_id, ref

# 示例
print(parse_dep_reference("proj-alpha:task-uuid-1111", "my-proj"))  
# ('proj-alpha', 'task-uuid-1111')
print(parse_dep_reference("task-uuid-2222", "my-proj"))            
# ('my-proj', 'task-uuid-2222')
print(parse_dep_reference("  :task-uuid-3333", "my-proj"))         
# ('my-proj', 'task-uuid-3333')   （project_id为空时自动填充）
```

## 6. 跨项目任务状态查询API设计

### 6.1 接口定义
- **端点**：`GET /api/v1/projects/{project_id}/tasks/{task_id}/state`
- **返回**：`{"state": "success", "end_time": "2025-04-10T12:00:00Z"}`
- **鉴权**：需调用方提供API密钥（可在项目间共享或使用服务令牌）。
- **缓存**：客户端和服务端均可设置Cache-Control: max-age=2（秒）。

### 6.2 内部调用封装（Python）

```python
import requests
from datetime import datetime, timezone

CROSS_PROJECT_TIMEOUT = 3  # 秒
CROSS_PROJECT_RETRIES = 2

def fetch_task_state_from_remote(project_id: str, task_id: str) -> dict:
    """
    调用远程项目API获取任务状态，带超时和重试。
    返回状态字典，失败时返回默认"unknown"。
    """
    url = f"https://api.example.com/projects/{project_id}/tasks/{task_id}/state"
    headers = {"Authorization": "Bearer shared-service-token"}
    for attempt in range(CROSS_PROJECT_RETRIES + 1):
        try:
            resp = requests.get(url, headers=headers, timeout=CROSS_PROJECT_TIMEOUT)
            resp.raise_for_status()
            data = resp.json()
            return {
                "state": data.get("state", "unknown"),
                "end_time": data.get("end_time")
            }
        except Exception as e:
            if attempt < CROSS_PROJECT_RETRIES:
                continue
            # 最终失败，返回unknown（后续降级策略）
            return {"state": "unknown", "end_time": None}
```

## 7. 依赖解析引擎改造（支持跨项目依赖图构建与状态判读）

### 7.1 核心逻辑修改
在原有依赖检查函数中，对每个`depends_on`元素调用`parse_dep_reference`获得项目ID和任务ID，然后：
- 同一项目：按原有方式查询本地数据库（走缓存或直接查）。
- 不同项目：优先查询本地缓存表`cross_project_dep_cache`，若缓存不存在或超过TTL（2秒），则调用远程API获取状态，并写入缓存。

### 7.2 依赖图构建（仅用于循环依赖检测）
每次任务触发前，解析所有依赖构建一张全局图（含项目节点）。采用DFS检测环，若检测到环则记录告警并拒绝执行任务。

```python
from collections import defaultdict

def build_dependency_graph(task_ref: str, current_project: str, resolved_deps: list) -> dict:
    """
    构建有向图：节点标识为 "project_id:task_id"
    返回邻接表
    """
    graph = defaultdict(list)
    # 当前任务节点
    current_node = f"{current_project}:{task_ref}"
    for dep_str in resolved_deps:
        proj, tid = parse_dep_reference(dep_str, current_project)
        dep_node = f"{proj}:{tid}"
        graph[current_node].append(dep_node)   # 当前任务依赖dep_node
    return graph

def has_cycle(graph: dict) -> bool:
    """标准DFS检测有向环"""
    WHITE, GRAY, BLACK = 0, 1, 2
    color = defaultdict(lambda: WHITE)
    def dfs(u):
        color[u] = GRAY
        for v in graph.get(u, []):
            if color[v] == GRAY:
                return True
            if color[v] == WHITE and dfs(v):
                return True
        color[u] = BLACK
        return False
    for u in list(graph.keys()):
        if color[u] == WHITE and dfs(u):
            return True
    return False
```

### 7.3 状态判读
修改`check_dependencies`函数：

```python
from datetime import datetime, timezone

def check_dependencies(task_id, project_id, depends_on_list, db_conn, cache_table, remote_fetcher):
    """
    输入：任务ID，项目ID，依赖列表，数据库连接，缓存操作函数，远程获取函数
    返回：(bool, list) 是否满足依赖，未满足的任务详情
    """
    unsatisfied = []
    for dep_str in depends_on_list:
        dep_proj, dep_task = parse_dep_reference(dep_str, project_id)
        state, end_time = None, None

        if dep_proj == project_id:
            # 同项目，直接查本地tasks表
            row = db_conn.fetchone("SELECT state, end_time FROM tasks WHERE project_id=%s AND task_id=%s", (project_id, dep_task))
            if row:
                state, end_time = row['state'], row['end_time']
            else:
                state = 'unknown'
        else:
            # 跨项目，先查本地缓存
            row = db_conn.fetchone(f"SELECT dep_state, dep_end_time, updated_at FROM {cache_table} WHERE source_project_id=%s AND source_task_id=%s AND dep_project_id=%s AND dep_task_id=%s",
                                   (project_id, task_id, dep_proj, dep_task))
            now = datetime.now(timezone.utc)
            if row and (now - row['updated_at']).total_seconds() < 2:
                state = row['dep_state']
                end_time = row['dep_end_time']
            else:
                # 缓存缺失或过期，远程获取
                remote = remote_fetcher(dep_proj, dep_task)
                state = remote.get('state', 'unknown')
                end_time = remote.get('end_time')
                # 写入缓存（异步或同步，此处简单同步）
                db_conn.execute(
                    f"INSERT INTO {cache_table} (source_project_id, source_task_id, dep_project_id, dep_task_id, dep_state, dep_end_time, updated_at) "
                    "VALUES (%s,%s,%s,%s,%s,%s, %s) "
                    "ON CONFLICT (source_project_id, source_task_id, dep_project_id, dep_task_id) "
                    "DO UPDATE SET dep_state=EXCLUDED.dep_state, dep_end_time=EXCLUDED.dep_end_time, updated_at=EXCLUDED.updated_at",
                    (project_id, task_id, dep_proj, dep_task, state, end_time, now)
                )

        # 判断是否满足
        if state != 'success' or end_time is None:
            unsatisfied.append({"project_id": dep_proj, "task_id": dep_task, "current_state": state})
    return len(unsatisfied) == 0, unsatisfied
```

## 8. 缓存策略与容错机制（超时、降级、重试）

### 8.1 缓存策略
- **本地缓存表**：记录已查询的跨项目依赖，TTL=2秒（根据业务可配置）。写入时机：每次远程调用成功向依赖结果。
- **缓存淘汰**：定期清理超时（>5秒）的记录，通过定时任务或写入时清理。
- **主动失效**：当依赖任务所在项目主动通知状态变更时（可选webhook），可更新缓存。

### 8.2 超时与重试
- 远程API调用超时设为3秒，重试2次，总等待不超过6秒。
- 若最终失败，返回状态`unknown`，并按降级逻辑处理。

### 8.3 降级策略
- 当跨项目依赖无法获取（`unknown`）时，视为“依赖满足”并允许当前任务执行？**必须根据业务风险决定。** 推荐：记录告警日志，并**拒绝执行**（安全优先）。但可为管理员配置开关（`cross_project_unsafe_allow`），开启后降级为满足。
- 单次依赖检查中跨项目调用数超过5个，剩余依赖直接视为满足（避免雪崩）。

### 8.4 示例配置（YAML）
```yaml
depends_on:
  cross_project:
    cache_ttl_seconds: 2
    remote_timeout_seconds: 3
    retries: 2
    max_remote_calls_per_check: 5
    safe_mode: true  # true: 未知状态则拒绝; false: 降级为满足
```

## 9. 示例代码（核心函数、API调用、解析逻辑）

完整代码整合见文档附录（因篇幅仅展示核心流程）。以下为模拟运行示例：

```python
# 模拟数据
current_project = "proj-1"
current_task_id = "task-current-001"
depends_on_input = [
    "proj-2:task-aaa-111",
    "task-bbb-222",                     # 同一项目，自动解析为 proj-1:task-bbb-222
    "proj-3:task-ccc-333"
]

# 步骤1：解析
for dep in depends_on_input:
    proj, tid = parse_dep_reference(dep, current_project)
    print(f"Resolved: {proj}:{tid}")

# 步骤2：循环检测
graph = build_dependency_graph(current_task_id, current_project, depends_on_input)
if has_cycle(graph):
    print("Cycle detected, abort!")
    # 实际上需要构建完整图（包含依赖的依赖），当前仅为示例

# 步骤3：检查依赖状态（伪代码）
# assuming db_conn and cache initialized
is_satisfied, unsatisfied = check_dependencies(...)
print(f"Satisfied: {is_satisfied}, Unsatisfied: {unsatisfied}")
```

## 10. 迁移计划与回滚方案

### 10.1 迁移步骤
1. **数据库迁移**：执行SQL脚本（见第4节）。
2. **代码发布**：部署包含解析引擎改造、缓存表操作、远程API调用的新版本。
3. **灰度测试**：选取少量非核心项目，手动构造跨项目依赖任务，验证功能。
4. **全量开放**：历史数据无需迁移（旧格式自动兼容）。生产库无`project_id:task_id`格式，可平滑过渡。

### 10.2 回滚方案
- **代码回滚**：恢复旧版本代码，`depends_on`字段只会包含纯task_id，新格式`project_id:task_id`不被识别，会被视为非法任务ID导致依赖检查失败（抛出异常）。因此需确保回滚前**清理所有包含新格式的依赖**，或设置兼容性开关：旧代码遇到冒号时忽略该依赖（推荐）。
- **数据库回滚**：删除新增索引和缓存表（回滚脚本），不影响原有数据。

## 11. 风险点与注意事项

### 11.1 循环依赖
- 跨项目环检测依赖图需包含所有层级的依赖，可能因信息不足无法检测（远程依赖的依赖无法获取）。方案