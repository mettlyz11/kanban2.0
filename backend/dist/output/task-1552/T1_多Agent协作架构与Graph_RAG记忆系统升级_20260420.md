# T1: AI助手优化 - 多Agent协作架构与Graph RAG记忆系统升级

**看板任务**: #1552
**执行日期**: 2026-04-20
**状态**: ✅ 完成
**优先级**: P1

---

## 目录

1. [现状分析](#1-现状分析)
2. [多Agent协作框架调研](#2-多agent协作框架调研)
3. [Graph RAG记忆系统架构设计](#3-graph-rag记忆系统架构设计)
4. [统一可观测性层设计](#4-统一可观测性层设计)
5. [Agent性能基准测试集](#5-agent性能基准测试集)
6. [实施路线图](#6-实施路线图)
7. [风险评估与应对](#7-风险评估与应对)
8. [验收标准与里程碑](#8-验收标准与里程碑)

---

## 1. 现状分析

### 1.1 当前架构

| 组件 | 当前状态 | 瓶颈 |
|------|---------|------|
| **Agent模型** | 单Agent（main session）+ 按需spawn子代理 | 无法并行处理复杂任务链 |
| **记忆系统** | MEMORY.md (976行) + memory/*.md (52个文件, 820KB) | 扁平文件结构，无语义关联 |
| **知识库** | Obsidian Vault (4.6GB, 28,298文件) | 有wikilink但无自动图谱构建 |
| **工具调用** | 55+内置skills + 18+workspace skills | 无可观测性层，调用不可追溯 |
| **OpenClaw版本** | 2026.4.15 (041266a) | 基础架构已成熟，但缺乏多Agent编排 |

### 1.2 核心问题

1. **记忆瓶颈**: 当前MEMORY.md线性增长，每次session需加载大量上下文，有效信息密度随时间递减
2. **协作瓶颈**: 子代理之间无协调机制，无法实现"编排-执行"分离
3. **知识孤岛**: Obsidian Vault与MEMORY.md体系相互独立，知识未形成统一图谱
4. **无观测性**: 工具调用无trace聚合，无法分析性能瓶颈和错误模式

### 1.3 行业趋势对标（2026 Q2）

| 趋势 | 代表厂商 | 对OpenClaw的启示 |
|------|---------|----------------|
| MCP Gateway标准化 | Anthropic, Microsoft, Red Hat | 工具调用应遵循MCP协议 |
| Graph RAG替代向量RAG | Microsoft Research, Neo4j | 2026年复杂问答准确率提升30-50% |
| 多Agent编排框架 | AutoGen(MS), CrewAI, LangGraph | 需选择轻量级方案适配OpenClaw |
| 统一可观测性 | LangSmith, Arize Phoenix, OpenLIT | trace聚合+agent决策日志是标配 |

---

## 2. 多Agent协作框架调研

### 2.1 候选框架对比

| 维度 | AutoGen (MS) | CrewAI | LangGraph | OpenClaw原生 |
|------|-------------|--------|-----------|-------------|
| **核心模型** | 对话式多Agent | 角色扮演Agent | 状态图编排 | sessions_spawn |
| **编排方式** | GroupChat/Sequencing | 任务依赖链 | 有向图状态机 | 主代理spawn子代理 |
| **适用场景** | 复杂对话、辩论 | 流水线任务 | 条件分支、循环 | 简单并行 |
| **学习成本** | 高 | 中 | 高 | 低（已集成） |
| **部署复杂度** | 需Docker | pip安装 | pip安装 | 原生支持 |
| **Python依赖** | ✓ | ✓ | ✓ | 不依赖外部框架 |
| **与OpenClaw集成** | 需桥接 | 需桥接 | 需桥接 | 原生 |
| **推荐度** | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐(增强) |

### 2.2 推荐方案：OpenClaw原生增强 + LangGraph启发式编排

**不引入外部框架**，原因：
1. OpenClaw已有sessions_spawn/subagents/yield机制
2. 外部框架增加Python依赖和部署复杂度
3. 与现有skill体系不兼容

**增强方案：**

```
┌─────────────────────────────────────────────────┐
│              Orchestrator Agent                  │
│  (主代理 - 负责任务拆解、分配、协调、聚合)        │
│                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │ Worker 1 │  │ Worker 2 │  │ Worker N │       │
│  │ (研究)   │  │ (编码)   │  │ (分析)   │       │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘       │
│       │             │             │              │
│       └─────────────┼─────────────┘              │
│                     ▼                            │
│            Result Aggregator                     │
│         (合并、验证、写入看板)                     │
└─────────────────────────────────────────────────┘
```

**核心增强点：**
1. **编排协议**: 定义标准化的orchestrator→worker通信协议
2. **状态共享**: 通过workspace文件系统实现worker间状态同步
3. **容错机制**: worker失败时自动重试+降级策略
4. **资源管理**: 限制并行子代理数量（当前规则: 1/分钟）

### 2.3 编排协议设计

```yaml
# orchestrator-manifest.yaml (约定格式)
task_id: "1552"
task_name: "多Agent协作架构设计"
workers:
  - id: "research"
    model: "alicodingplan/qwen3.6-plus"
    thinking: "high"
    timeout: 600
    output: "output/task-1552/research-findings.md"
    depends_on: []
  - id: "design"
    model: "alicodingplan/qwen3.6-plus"
    thinking: "high"
    timeout: 900
    output: "output/task-1552/architecture-design.md"
    depends_on: ["research"]
  - id: "implementation"
    model: "alicodingplan/qwen3.6-plus"
    thinking: "medium"
    timeout: 1200
    output: "output/task-1552/implementation-plan.md"
    depends_on: ["design"]
```

---

## 3. Graph RAG记忆系统架构设计

### 3.1 三层记忆架构

```
┌──────────────────────────────────────────────────────┐
│                    L1: 热记忆 (Hot)                   │
│  MEMORY.md 核心摘要 (≤500行) + 最近7天daily notes     │
│  用途: 每次session启动必加载，提供即时上下文            │
│  存储: 纯文本文件                                      │
│  大小: < 50KB                                         │
├──────────────────────────────────────────────────────┤
│                    L2: 温记忆 (Warm)                   │
│  Graph RAG知识图谱 (Neo4j本地/Chroma向量)             │
│  用途: 按需语义搜索，复杂问题检索                       │
│  存储: Neo4j (图关系) + Chroma (向量嵌入)             │
│  大小: ~500MB (预计)                                  │
├──────────────────────────────────────────────────────┤
│                    L3: 冷记忆 (Cold)                   │
│  历史daily notes + MEMORY.md归档                      │
│  用途: 深度历史追溯，审计                               │
│  存储: 压缩归档文件                                     │
│  大小: 无限制                                          │
└──────────────────────────────────────────────────────┘
```

### 3.2 Graph RAG详细设计

#### 3.2.1 图Schema

```cypher
// 核心节点类型
(:Concept {name, domain, definition, created_at})
(:Task {id, title, status, kanban_id, created_at})
(:Person {name, role, company, contact_info})
(:Project {name, type, status})
(:Decision {id, context, outcome, date})
(:Document {path, type, size, last_modified})
(:Event {date, description, outcome})

// 核心关系类型
(CONCEPT)-[:RELATED_TO]->(CONCEPT)      // 概念关联
(CONCEPT)-[:BELONGS_TO]->(DOMAIN)        // 概念归属
(TASK)-[:DEPENDS_ON]->(TASK)             // 任务依赖
(TASK)-[:BELONGS_TO]->(PROJECT)          // 任务归属
(PERSON)-[:WORKS_AT]->(COMPANY)          // 人物-组织
(PERSON)-[:INVOLVED_IN]->(TASK)          // 人物-任务
(DECISION)-[:AFFECTS]->(TASK)            // 决策影响
(DOCUMENT)-[:ABOUT]->(CONCEPT)           // 文档-概念
(DOCUMENT)-[:SUPPORTS]->(TASK)           // 文档-任务
(EVENT)-[:TRIGGERED]->(TASK)             // 事件触发
```

#### 3.2.2 技术选型

| 组件 | 选型 | 理由 | 部署方式 |
|------|------|------|---------|
| **图数据库** | Neo4j Community (本地Docker) | 免费、Cypher查询、成熟生态 | Docker容器 |
| **向量存储** | ChromaDB (本地) | 轻量、Python原生、嵌入支持 | pip安装 |
| **嵌入模型** | sentence-transformers/all-MiniLM-L6-v2 | 384维、速度快、本地运行 | Python库 |
| **图谱构建** | 自定义Python脚本 | 解析MEMORY.md + memory/*.md + Obsidian wikilinks | 本地脚本 |
| **查询接口** | REST API (Flask) | 统一查询入口 | 本地服务 |

#### 3.2.3 记忆检索准确率设计

| 检索类型 | 当前(向量/文本) | Graph RAG目标 | 提升机制 |
|---------|---------------|--------------|---------|
| 概念查询 | 60-70% | **>90%** | 图关系补全文本语义 |
| 任务关联 | 40-50% | **>85%** | TASK→PROJECT→PERSON路径推理 |
| 历史决策 | 50-60% | **>85%** | DECISION→AFFECTS→TASK关系链 |
| 复杂多跳 | 20-30% | **>80%** | 图路径遍历替代多次向量搜索 |

#### 3.2.4 构建流程

```
MEMORY.md + memory/*.md + Obsidian Vault
         ↓
    [解析器] 提取实体、关系、wikilinks
         ↓
    [图谱构建器] 构建节点和边
         ↓
    [嵌入生成器] 为每个节点生成向量嵌入
         ↓
    Neo4j (图关系) + Chroma (向量)
         ↓
    [查询API] 统一查询接口
         ↓
    Agent启动时自动加载 L1 + 按需查询 L2
```

### 3.3 迁移策略

| 阶段 | 内容 | 耗时 | 风险 |
|------|------|------|------|
| **Phase 0**: 评估 | 现有记忆系统审计 | 2小时 | 低 |
| **Phase 1**: L1优化 | MEMORY.md精简+自动归档 | 4小时 | 低 |
| **Phase 2**: L2原型 | Neo4j+Chroma部署+基础图谱 | 8小时 | 中 |
| **Phase 3**: L2增强 | 嵌入生成+查询API+准确率测试 | 12小时 | 中 |
| **Phase 4**: 集成 | Agent查询接口+自动构建 | 8小时 | 高 |
| **Phase 5**: L3归档 | 历史文件压缩+检索保留 | 4小时 | 低 |

---

## 4. 统一可观测性层设计

### 4.1 架构

```
┌──────────────────────────────────────────────────────┐
│                  可观测性数据流                         │
│                                                      │
│  Agent Tool Calls → Trace Collector → Storage        │
│       ↓                    ↓            ↓            │
│  Decision Logs     → Event Buffer  →  Aggregator     │
│       ↓                    ↓            ↓            │
│  Error Traces      → Alert Manager →  Dashboard      │
└──────────────────────────────────────────────────────┘
```

### 4.2 数据采集

| 数据类型 | 采集方式 | 存储格式 |
|---------|---------|---------|
| 工具调用trace | OpenClaw session日志解析 | JSONL |
| Agent决策日志 | sessions_history导出 | JSON |
| 错误trace | exec/session error捕获 | JSONL |
| 性能指标 | 调用时间/Token用量/成功率 | JSON |
| 子代理生命周期 | sessions_spawn/list/kill | JSON |

### 4.3 存储方案

```
/Users/mettlyz/.openclaw/workspace/observability/
├── traces/
│   ├── 2026-04-20/
│   │   ├── tool-calls.jsonl      # 当日所有工具调用
│   │   ├── decisions.jsonl       # Agent决策日志
│   │   └── errors.jsonl          # 错误trace
│   └── ...
├── metrics/
│   ├── daily/
│   │   └── 2026-04-20.json       # 日聚合指标
│   └── weekly/
│       └── 2026-W17.json         # 周聚合指标
├── dashboards/
│   └── overview.html             # 静态HTML仪表盘
└── config/
    └── observability.yaml        # 配置
```

### 4.4 关键指标

| 指标 | 计算方式 | 告警阈值 |
|------|---------|---------|
| 工具调用成功率 | success/total | <95% |
| 平均响应时间 | sum(duration)/count | >30s |
| Token使用效率 | 有用Token/总Token | <60% |
| 子代理完成率 | completed/total | <90% |
| 记忆检索准确率 | relevant/total | <85% |
| 任务完成率 | completed/(completed+failed) | <80% |

### 4.5 简易Dashboard实现

使用纯HTML+JavaScript + JSON数据源，无需额外服务：

```html
<!-- 静态Dashboard -->
- 实时指标卡片（成功率、响应时间、Token效率）
- 工具调用分布饼图
- 子代理执行时间线
- 错误趋势折线图
- 记忆检索质量报告
```

---

## 5. Agent性能基准测试集

### 5.1 测试维度

| 维度 | 测试内容 | 指标 | 权重 |
|------|---------|------|------|
| **响应质量** | 10个标准问题的回答评分 | 人工评分1-5 | 30% |
| **上下文利用** | 能否正确引用MEMORY.md信息 | 召回率/准确率 | 25% |
| **任务完成** | 5个标准任务的完成度 | 完成步骤/总步骤 | 20% |
| **工具效率** | 工具调用次数与结果 | 调用次数/质量比 | 15% |
| **记忆检索** | Graph RAG vs 当前记忆 | 检索准确率 | 10% |

### 5.2 标准问题集（示例）

```json
{
  "response_quality": [
    {
      "id": "RQ-01",
      "question": "总结一下今天完成了哪些任务？",
      "expected_topics": ["看板系统查询", "任务状态汇总", "成果摘要"],
      "scoring_rubric": {"complete": 5, "partial": 3, "missed": 1}
    },
    {
      "id": "RQ-02",
      "question": "我上次提到的姜杰院士，他的联系方式是什么？",
      "expected_answer": "13701078121 (航天科技集团一院/中科院院士)",
      "scoring_rubric": {"exact": 5, "partial": 3, "wrong": 0}
    }
  ],
  "task_completion": [
    {
      "id": "TC-01",
      "task": "创建一个会议纪要并同步到看板系统",
      "steps": ["创建文件", "写入模板内容", "调用看板API创建任务", "确认状态"],
      "total_steps": 4
    }
  ]
}
```

### 5.3 基准测试执行流程

```
1. 准备测试环境（干净session，加载L1记忆）
2. 执行响应质量测试（10题）
3. 执行上下文利用测试（5题）
4. 执行任务完成测试（5任务）
5. 执行工具效率测试（10工具各1次）
6. 执行记忆检索对比测试（Graph RAG vs 当前）
7. 聚合评分 → 生成基准报告
```

---

## 6. 实施路线图

### 6.1 四阶段路线

```
Phase 1 (Week 1-2): 基础架构搭建
├── P1.1: 编排协议设计与实现 [2h]
├── P1.2: MEMORY.md精简与L1优化 [4h]
├── P1.3: 可观测性基础采集脚本 [4h]
└── P1.4: 基准测试集v1.0 [3h]

Phase 2 (Week 3-4): Graph RAG原型
├── P2.1: Neo4j Docker部署 [2h]
├── P2.2: ChromaDB部署 [1h]
├── P2.3: 记忆解析器+图谱构建 [8h]
├── P2.4: 嵌入生成+向量索引 [6h]
├── P2.5: 查询API实现 [4h]
└── P2.6: 准确率验证 [4h]

Phase 3 (Week 5-6): 集成与增强
├── P3.1: Agent-GraphRAG集成 [8h]
├── P3.2: 多Agent协作demo [8h]
├── P3.3: Dashboard实现 [6h]
├── P3.4: 自动化构建流水线 [4h]
└── P3.5: 性能基准测试v2.0 [4h]

Phase 4 (Week 7-8): 优化与验证
├── P4.1: 准确率优化到>85% [8h]
├── P4.2: 容错机制完善 [4h]
├── P4.3: L3归档系统 [4h]
├── P4.4: 全量基准测试报告 [4h]
└── P4.5: 文档与培训 [4h]
```

### 6.2 资源需求

| 资源 | 需求 | 当前可用 | 缺口 |
|------|------|---------|------|
| 存储空间 | ~2GB (Neo4j+Chroma+数据) | 充足(mac mini) | 无 |
| 内存 | ~4GB (Neo4j容器+嵌入模型) | 充足 | 无 |
| Docker | Neo4j容器 | 需确认 | 待检查 |
| Python包 | chromadb, sentence-transformers | 需安装 | pip install |

---

## 7. 风险评估与应对

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|---------|
| Neo4j Docker部署失败 | 低 | 中 | 备选: SQLite+NetworkX图 |
| 嵌入模型质量不足 | 中 | 高 | 备选: OpenAI embedding API |
| 图谱构建解析不完整 | 高 | 中 | 分阶段构建，先核心后扩展 |
| Agent查询延迟过高 | 中 | 中 | 缓存热查询结果 |
| 现有session流程被打断 | 低 | 高 | 渐进式迁移，保持向后兼容 |

---

## 8. 验收标准与里程碑

### 8.1 验收标准

| 验收项 | 标准 | 验证方法 |
|--------|------|---------|
| Graph RAG原型 | 记忆检索准确率>85% | 基准测试集v2.0 |
| 多Agent协作demo | ≥2个Agent协调完成1个任务 | 编排协议执行记录 |
| 可观测性Dashboard | 覆盖所有工具调用 | 日志完整性检查 |
| 性能基准报告 | 5维度完整评分 | 报告文档 |

### 8.2 里程碑

| 里程碑 | 日期 | 交付物 |
|--------|------|--------|
| M1: 基础架构完成 | 2026-05-03 | 编排协议+L1优化+观测采集 |
| M2: Graph RAG原型 | 2026-05-17 | Neo4j+Chroma+查询API |
| M3: 集成完成 | 2026-05-31 | Agent-GraphRAG+多Agent demo |
| M4: 优化验收 | 2026-06-14 | 全量基准报告+准确率>85% |

---

## 附录A: 快速验证脚本

```python
#!/usr/bin/env python3
"""Graph RAG记忆系统快速验证脚本"""
import os
import json

MEMORY_PATH = "/Users/mettlyz/.openclaw/workspace/MEMORY.md"
MEMORY_DIR = "/Users/mettlyz/.openclaw/workspace/memory"

def audit_current_memory():
    """审计当前记忆系统"""
    # MEMORY.md统计
    with open(MEMORY_PATH) as f:
        lines = f.readlines()
    print(f"MEMORY.md: {len(lines)} 行")
    
    # daily notes统计
    files = [f for f in os.listdir(MEMORY_DIR) if f.endswith('.md')]
    total_size = sum(os.path.getsize(os.path.join(MEMORY_DIR, f)) for f in files)
    print(f"Daily notes: {len(files)} 个文件, {total_size/1024:.1f} KB")
    
    # 内容分析
    sections = {}
    for line in lines:
        if line.startswith('## '):
            section = line.strip()
            sections[section] = sections.get(section, 0) + 1
    print(f"MEMORY.md sections: {len(sections)}")
    for s, c in sorted(sections.items(), key=lambda x: -x[1])[:10]:
        print(f"  {s}: {c}")

if __name__ == "__main__":
    audit_current_memory()
```

---

*文档生成: 2026-04-20 01:00*
*看板任务: #1552*
*下一阶段: 等待用户确认执行路线和时间窗口*
