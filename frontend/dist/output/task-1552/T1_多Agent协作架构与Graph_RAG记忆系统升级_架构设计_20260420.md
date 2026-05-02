# T1: 多Agent协作架构与Graph RAG记忆系统升级

> **看板任务**: #1552
> **生成时间**: 2026-04-20 11:40 CST
> **版本**: 1.0
> **状态**: 架构设计完成，待执行

---

## 📊 执行摘要

**当前状态**: OpenClaw系统已实现基础记忆图谱(18概念/12关系/10规则)和V4.2调度器(LLM驱动任务生成)，但记忆检索仍为线性匹配，多Agent间缺乏智能路由和状态管理能力。

**升级目标**: 
1. 将记忆系统从JSONL文件升级为支持语义搜索+图遍历的Graph RAG架构
2. 构建多Agent协作编排层，实现智能任务路由/能力注册/对话协议
3. 将子代理启动开销从~10s降至5-7s，并发效率提升50%+

**预期效果**: 记忆召回准确率+40%，复杂任务执行效率+60%，跨Agent知识共享从0到1。

---

## 一、现状诊断

### 1.1 记忆系统现状

| 组件 | 当前状态 | 评分 | 问题 |
|------|---------|------|------|
| **概念图谱** | 18个概念，7分类，12关系 | ⚠️ 6/10 | JSONL扁平存储，无图遍历能力 |
| **实体关系** | 7条关系（业务/学术/联系人） | ⚠️ 5/10 | 仅手动维护，无自动发现 |
| **规则库** | 10条行为规则 | ✅ 8/10 | 覆盖全面，但无动态推理 |
| **衰减机制** | 1%/日衰减，召回+10% | ⚠️ 6/10 | 线性衰减，无语义相似度加权 |
| **召回方式** | memory_search(语义搜索) | ⚠️ 5/10 | 纯向量搜索，无图路径推理 |
| **知识图谱** | 3层架构已设计(Obsidian) | 🔄 4/10 | 架构文档存在但未落地 |

### 1.2 多Agent协作现状

| 组件 | 当前状态 | 评分 | 问题 |
|------|---------|------|------|
| **调度器** | V4.2 LLM驱动任务生成 | ✅ 7/10 | 仅任务生成，无运行时编排 |
| **子代理启动** | sessions_spawn，~10s开销 | ⚠️ 5/10 | 31k上下文传输开销大 |
| **并发控制** | 1个/分钟手动限制 | ⚠️ 4/10 | 无动态并发管理 |
| **Agent间通信** | 仅sessions_send单向 | ❌ 3/10 | 无结构化协议，无状态共享 |
| **能力注册** | 无 | ❌ 0/10 | 调度器不知道各Agent能力 |
| **状态管理** | 无 | ❌ 0/10 | 任务分解后无整体状态追踪 |

### 1.3 基准数据（2026-04-20 10:33测试）

| 指标 | 值 | 目标 |
|------|-----|------|
| 子代理启动开销 | ~10s (31k上下文) | ≤5s |
| 最优并发 | n=10 (32/s) | n=15 (40/s) |
| CPU单核基准 | 0.33s | — |
| 内存可用 | 44GB/64GB (31%使用) | — |
| 会话文件数 | 184 (0过期) | <200 |

---

## 二、Graph RAG记忆系统升级方案

### 2.1 架构设计

```
┌──────────────────────────────────────────────────────────────┐
│                    Graph RAG Memory System                     │
├──────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────┐  │
│  │  L1: 向量层  │  │  L2: 图结构层 │  │   L3: 语义推理层     │  │
│  │ (Embedding) │  │  (Graph DB)  │  │  (Reasoning Engine) │  │
│  └──────┬──────┘  └──────┬───────┘  └────────┬────────────┘  │
│         │                │                    │               │
│  ┌──────┴────────────────┴────────────────────┴──────────┐   │
│  │              Memory Retrieval Pipeline                  │   │
│  │  Query → 向量粗筛 → 图路径精筛 → 语义排序 → Top-K返回   │   │
│  └───────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
         ↓                    ↓                     ↓
  memory/*.md (markdown)  graph/*.jsonl       memory_search()
  MEMORY.md              relations.jsonl      + graph traversal
  daily notes            entities.jsonl       + semantic ranking
```

### 2.2 三层记忆架构

#### L1: 向量层 (Embedding Layer)
- **功能**: 所有记忆内容的向量化索引
- **实现**: 使用轻量级embedding模型（如text-embedding-3-small或本地模型）
- **索引内容**:
  - 18个概念（concepts.jsonl）→ 向量 + 元数据
  - 7个实体关系（entities.jsonl）→ 向量 + 元数据
  - 10条规则（rules.jsonl）→ 向量 + 触发条件
  - MEMORY.md 核心条目 → 分段向量化
  - 近7天daily notes → 每日摘要向量化
- **数据结构**: 本地SQLite + embedding向量列（避免外部依赖）

#### L2: 图结构层 (Graph Layer)
- **功能**: 概念/实体/规则之间的关系网络
- **升级内容**:
  - 从12条关系扩展至50+条（自动发现 + 手动维护）
  - 增加关系类型：`depends_on`, `enhances`, `contradicts`, `subsumes`, `implements`
  - 增加权重衰减：关系强度随时间衰减（0.5%/日）
  - 增加反向索引：每个节点维护入边/出边列表
- **图遍历能力**:
  - 1-hop: 直接关联节点召回
  - 2-hop: 关联的关联（如：概念A→概念B→规则R）
  - 路径发现：找出两个概念之间的最短路径

#### L3: 语义推理层 (Reasoning Layer)
- **功能**: 基于图结构的多跳推理
- **能力**:
  - **关系推理**: "A依赖B，B增强C → A间接受益于C"
  - **冲突检测**: "规则R1要求审核，规则R2要求自动执行 → 冲突"
  - **上下文增强**: 基于图路径动态扩展检索上下文
  - **记忆融合**: 多个来源的记忆合并去重

### 2.3 召回流程升级

```
当前流程:
Query → memory_search (语义匹配) → Top-K结果

升级后流程:
Query → L1向量粗筛 (Top-20) → L2图路径扩展 (+邻居节点) → L3语义排序 → Top-K返回

效果:
- 召回率: 60% → 90%+
- 精确率: 70% → 85%+
- 多跳查询支持: 无 → 3-hop
```

### 2.4 记忆衰减机制升级

| 维度 | 当前 | 升级后 |
|------|------|--------|
| **时间衰减** | 1%/日线性 | 指数衰减 (半衰期30天) |
| **使用衰减** | 无 | 每次召回+5%权重（上限+50%） |
| **关联衰减** | 无 | 关联节点的活跃度传导（0.3%/日） |
| **语义衰减** | 无 | 与当前任务域相似度加权 |
| **归档阈值** | 20% | 动态阈值（基于总容量） |

### 2.5 实施计划

| Phase | 内容 | 工作量 | 优先级 |
|-------|------|--------|--------|
| **P0: 向量层** | SQLite+embedding索引，18概念+10规则+核心MEMORY条目 | 2h | ⭐⭐⭐ |
| **P1: 图扩展** | 关系扩展至50+，增加5种关系类型，反向索引 | 3h | ⭐⭐⭐ |
| **P2: 召回增强** | 3阶段检索管道（向量→图→排序） | 4h | ⭐⭐ |
| **P3: 语义推理** | 关系推理+冲突检测+上下文增强 | 4h | ⭐⭐ |
| **P4: 自动化** | 每日自动维护+质量监控 | 2h | ⭐ |

---

## 三、多Agent协作架构升级方案

### 3.1 架构设计

```
┌──────────────────────────────────────────────────────────────┐
│                   Multi-Agent Orchestrator                     │
├──────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────────────┐  │
│  │ 能力注册中心 │  │  智能任务路由  │  │   状态管理引擎       │  │
│  │(Capability  │  │ (Task Router)│  │  (State Manager)    │  │
│  │  Registry)  │  │              │  │                     │  │
│  └──────┬──────┘  └──────┬───────┘  └────────┬────────────┘  │
│         │                │                    │               │
│  ┌──────┴────────────────┴────────────────────┴──────────┐   │
│  │              Agent Communication Protocol               │   │
│  │  Task Dispatch → Status Report → Result Aggregation     │   │
│  └───────────────────────────────────────────────────────┘   │
│         │                │                    │               │
│  ┌──────┴──────┐  ┌──────┴──────┐  ┌─────────┴──────────┐   │
│  │ Research    │  │ Analysis    │  │ Execution           │   │
│  │ Agent       │  │ Agent       │  │ Agent               │   │
│  │ (研究/搜索)  │  │ (分析/规划)  │  │ (执行/操作)         │   │
│  └─────────────┘  └─────────────┘  └────────────────────┘   │
└──────────────────────────────────────────────────────────────┘
```

### 3.2 能力注册中心 (Capability Registry)

**设计目标**: 让调度器知道"谁能做什么"

```yaml
# registry format
capabilities:
  - id: research_agent
    name: "研究代理"
    skills:
      - web_search (Tavily)
      - paper_download
      - market_analysis
    max_concurrent: 2
    avg_completion_time: 120s  # seconds
    context_window: 32k
    cost_per_task: ~$0.05
    success_rate: 0.92
    
  - id: analysis_agent
    name: "分析代理"
    skills:
      - data_analysis
      - report_generation
      - strategy_planning
    max_concurrent: 1
    avg_completion_time: 180s
    context_window: 32k
    cost_per_task: ~$0.08
    success_rate: 0.88

  - id: execution_agent
    name: "执行代理"
    skills:
      - file_operations
      - kanban_sync
      - data_entry
    max_concurrent: 3
    avg_completion_time: 60s
    context_window: 16k
    cost_per_task: ~$0.03
    success_rate: 0.95

  - id: wiki_agent
    name: "知识库代理"
    skills:
      - wiki_update
      - knowledge_graph_maintenance
      - content_classification
    max_concurrent: 1
    avg_completion_time: 90s
    context_window: 32k
    cost_per_task: ~$0.06
    success_rate: 0.90
```

### 3.3 智能任务路由 (Task Router)

**路由策略**:

```
任务输入
    ↓
[1] 任务分类 (LLM判断类型)
    ↓
[2] 能力匹配 (查询Capability Registry)
    ↓
[3] 路由决策:
    ├── 单Agent任务 → 直接分配
    ├── 多Agent任务 → 任务分解 + 顺序/并行调度
    └── 需要Memory → 先激活Graph RAG检索上下文
    ↓
[4] 上下文优化:
    ├── 动态上下文裁剪 (31k → 15k以下)
    ├── 记忆注入 (Graph RAG Top-5)
    └── 任务模板填充
    ↓
[5] 执行 + 监控
```

**任务分类矩阵**:

| 任务类型 | 特征 | 推荐Agent | 上下文策略 |
|---------|------|----------|-----------|
| 研究报告 | 需要搜索+分析 | research → analysis | 32k + Memory注入 |
| 数据处理 | 文件操作+看板同步 | execution | 16k 精简 |
| 知识维护 | Wiki更新+KG维护 | wiki | 32k + KG上下文 |
| 复杂规划 | 多步骤决策 | analysis → execution | 32k + 全量Memory |
| 快速执行 | 单一操作 | execution | 8k 最小 |

### 3.4 Agent通信协议 (ACP)

**消息格式**:

```json
{
  "message_id": "msg-uuid",
  "from": "orchestrator",
  "to": "research_agent",
  "type": "task_dispatch",
  "timestamp": "2026-04-20T11:40:00+08:00",
  "payload": {
    "task_id": "#1552",
    "task_type": "research",
    "priority": "high",
    "context": {
      "memory_snippets": ["..."],
      "related_tasks": ["#1537", "#1579"],
      "constraints": ["max_results=5", "tavily_only"]
    },
    "instructions": "...",
    "expected_output": "markdown report",
    "timeout_seconds": 300
  },
  "metadata": {
    "kanban_task": "#1552",
    "session_label": "research-1552-01"
  }
}
```

**消息类型**:
- `task_dispatch`: 任务派发
- `status_report`: 进度报告 (heartbeat)
- `result_submit`: 结果提交
- `context_request`: 上下文请求
- `escalation`: 升级请求（需要人类介入）
- `handoff`: 任务移交（Agent→Agent）

### 3.5 状态管理引擎

**任务状态机**:

```
PENDING → DISPATCHED → RUNNING → COMPLETED
                ↓           ↓
            FAILED ←── TIMEOUT
                ↓
            RETRY (max 2) → FAILED
```

**全局状态追踪**:

```yaml
# multi-agent task state
task_group:
  id: "tg-1552"
  parent_task: "#1552"
  status: in_progress
  sub_tasks:
    - id: "st-001"
      agent: research_agent
      status: completed
      result: "report.md"
      time_taken: 95s
    - id: "st-002"
      agent: analysis_agent
      status: running
      started_at: "2026-04-20T11:42:00+08:00"
    - id: "st-003"
      agent: execution_agent
      status: pending
      depends_on: ["st-002"]
  aggregate_result: null  # 所有完成后生成
  total_time: null
```

### 3.6 实施计划

| Phase | 内容 | 工作量 | 优先级 |
|-------|------|--------|--------|
| **P0: 能力注册** | 定义4类Agent能力矩阵 + registry文件 | 1h | ⭐⭐⭐ |
| **P1: 任务路由** | 任务分类逻辑 + Agent选择算法 | 2h | ⭐⭐⭐ |
| **P2: 通信协议** | ACP消息格式 + 状态追踪 | 2h | ⭐⭐ |
| **P3: 上下文优化** | 动态上下文裁剪 (31k→15k) | 2h | ⭐⭐ |
| **P4: 状态管理** | 全局状态机 + 聚合报告 | 3h | ⭐ |

---

## 四、关键优化点

### 4.1 子代理启动优化 (~10s → 5-7s)

| 优化项 | 方法 | 预期效果 |
|--------|------|---------|
| **上下文裁剪** | AGENTS.md/SOUL.md等仅注入关键部分 | -8k tokens |
| **延迟加载** | 非必需文件按需读取，不在bootstrap注入 | -5k tokens |
| **模板缓存** | 常用任务模板预加载 | -2s启动 |
| **轻量上下文** | lightContext=true 用于简单任务 | -50% bootstrap |

### 4.2 并发管理优化

| 当前 | 目标 | 方法 |
|------|------|------|
| 1个/分钟限制 | 动态并发(2-5个/分钟) | 基于任务类型和资源使用动态调整 |
| 手动控制 | 自动调度 | Orchestrator自动管理 |
| 无优先级 | 优先级队列 | P0任务插队 |

### 4.3 记忆-任务联动

```
任务启动
    ↓
Graph RAG 检索相关记忆
    ↓
注入上下文（Top-5相关记忆片段）
    ↓
Agent执行（有历史上下文）
    ↓
执行结果 → 更新记忆图谱
    ↓
新关系自动发现
```

---

## 五、风险评估

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| 过度工程化 | 中 | 高 | 分阶段实施，每阶段可独立验证 |
| 性能退化 | 低 | 高 | 每阶段基准测试对比 |
| 记忆噪声增加 | 中 | 中 | 严格质量门控 + 衰减机制 |
| Agent冲突 | 低 | 中 | 能力注册 + 任务去重 |
| 上下文超限 | 中 | 中 | 动态裁剪 + 分层注入 |

---

## 六、执行路线

### Phase 1: Graph RAG基础 (Week 1-2, 4/20-5/3)
- [ ] P0: 创建SQLite embedding索引（18概念+10规则+核心Memory条目）
- [ ] P1: 关系扩展至50+条，增加5种关系类型
- [ ] P0: 实现3阶段检索管道原型
- [ ] 验证: 召回率对比测试

### Phase 2: 多Agent基础 (Week 2-3, 5/4-5/17)
- [ ] P0: 能力注册中心（4类Agent定义）
- [ ] P1: 任务路由算法实现
- [ ] P2: ACP通信协议 + 状态追踪
- [ ] 验证: 多Agent协作任务测试

### Phase 3: 集成优化 (Week 3-4, 5/18-5/31)
- [ ] P3: 语义推理层实现
- [ ] P4: 上下文优化（31k→15k）
- [ ] 子代理启动优化
- [ ] 验证: 端到端基准测试

### Phase 4: 自动化 (Week 4-5, 6/1-6/14)
- [ ] 每日自动维护脚本
- [ ] 质量监控Dashboard
- [ ] 自动关系发现
- [ ] 验证: 30天稳定性测试

---

## 七、成功标准

| 指标 | 当前 | Phase 1目标 | Phase 3目标 |
|------|------|------------|------------|
| 记忆召回准确率 | ~60% | ≥80% | ≥90% |
| 多跳查询支持 | 不支持 | 2-hop | 3-hop |
| 子代理启动开销 | ~10s | — | ≤5s |
| 并发效率 | 1/分钟 | 2/分钟 | 5/分钟 |
| 跨Agent知识共享 | 无 | 基础 | 完整 |
| 记忆图谱关系数 | 12 | 50+ | 100+ |
| 任务路由准确率 | N/A | — | ≥85% |

---

## 八、产出文件清单

| 文件 | 路径 | 说明 |
|------|------|------|
| 架构设计文档 | `output/task-1552/` (本文档) | 完整升级方案 |
| 能力注册文件 | `memory/graph/capabilities.json` | 4类Agent定义 |
| Graph RAG索引 | `memory/graph/embeddings.db` | SQLite向量索引 |
| 关系扩展 | `memory/graph/relations.jsonl` | 50+条关系 |
| 检索管道脚本 | `scripts/graph_rag_retrieval.py` | 3阶段检索 |
| 任务路由器 | `scripts/task_router.py` | 分类+路由逻辑 |
| ACP协议定义 | `memory/graph/acp_protocol.md` | 消息格式规范 |
| 状态管理 | `scripts/state_manager.py` | 全局状态追踪 |
| 执行报告 | `output/task-1552/execution_report.md` | 实施记录 |

---

*文档版本: 1.0 | 创建: 2026-04-20 | 任务: #1552*
