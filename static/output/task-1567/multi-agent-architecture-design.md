# 多Agent协作工作流架构设计文档

**看板任务**: #1567  
**目标**: T1 - AI助手优化  
**版本**: V1.0  
**日期**: 2026-04-20  
**设计原则**: LLM + 深度推理优先，不惜时间/金钱，只追求质量

---

## 一、现有架构分析（V4.2 → V4.4 升级基线）

### 1.1 当前架构（V4.2）

```
┌─────────────────────────────────────────────────┐
│           Self-Driving Scheduler V4.2            │
│                                                  │
│  ┌─────────────┐    ┌─────────────────────────┐  │
│  │  调度循环    │───→│  子代理批量启动（≤5并发） │  │
│  │  (5min周期)  │    │  (openclaw cron add)    │  │
│  └──────┬──────┘    └─────────────────────────┘  │
│         │                                         │
│         ↓                                         │
│  ┌─────────────────────────────────────────────┐  │
│  │  LLM 任务生成子代理（pending < 10触发）       │  │
│  │  单一LLM完成：分析→Research→生成→去重→写入    │  │
│  └─────────────────────────────────────────────┘  │
│                                                   │
│  ┌─────────────────────────────────────────────┐  │
│  │  Kanban RDS (MySQL)                          │  │
│  │  tasks / projects / goals                    │  │
│  └─────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────┘
```

### 1.2 V4.2 架构痛点

| 痛点 | 影响 | 严重程度 |
|------|------|---------|
| **单Agent全栈**：一个LLM子代理完成分析+Research+生成+去重+写入 | 上下文过长导致推理质量下降 | 🔴 高 |
| **Research质量受限**：单一LLM生成的Research查询不够深入 | 任务生成质量上限受限于单LLM | 🔴 高 |
| **无质量审核**：生成即写入，无独立去重/审核环节 | 重复/低质量任务进入看板 | 🟡 中 |
| **无版本隔离**：task_generator.py → v4 → v4.2 并行存在 | 去重困难，可能重复生成 | 🟡 中 |
| **可观测性弱**：仅靠日志，无结构化监控 | 故障排查困难 | 🟡 中 |
| **无并行Research**：Research查询顺序执行 | 任务生成耗时长 | 🟢 低 |
| **无失败重试策略**：spawn失败后仅记录 | 任务可能丢失 | 🟡 中 |

### 1.3 行业最佳实践（2025-2026）

基于Anthropic、Microsoft Azure Architecture Center等最新研究：

| 模式 | 适用场景 | 来源 |
|------|---------|------|
| **Orchestrator-Worker** | 复杂任务分解，Lead Agent协调 | Anthropic Engineering |
| **Sequential Pipeline** | 标准化处理流程 | Microsoft AI Design Patterns |
| **Parallel Research** | 多源信息收集 | 2025 Multi-Agent Survey |
| **Human-in-the-Loop** | 关键决策审核 | Enterprise AI Best Practices |
| **Shared State + Message Queue** | Agent间通信 | HALO Architecture Paper |

---

## 二、多Agent架构设计（V4.4）

### 2.1 总体架构

```
┌────────────────────────────────────────────────────────────────────────┐
│                    Multi-Agent Self-Driving System V4.4                │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                     🎯 Orchestrator Agent (规划Agent)             │  │
│  │  职责: 目标差距分析、任务编排、优先级排序、生命周期管理            │  │
│  │  模型: qwen3.6-plus (高推理能力)                                  │  │
│  └──────┬──────────────┬──────────────┬──────────────────────┬──────┘  │
│         │ 触发         │ 触发         │ 触发               │ 触发     │
│         ▼              ▼              ▼                    ▼          │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐  │
│  │ 🔍 Research  │ │ 🔍 Research  │ │ 🔍 Research  │ │ 🔍 Research  │  │
│  │   Agent #1   │ │   Agent #2   │ │   Agent #3   │ │   Agent #4   │  │
│  │ (T1/T2领域)  │ │ (T3/T4领域)  │ │ (T5/T6领域)  │ │ (T7/跨领域)  │  │
│  │              │ │              │ │              │ │              │  │
│  │ Tavily搜索   │ │ Tavily搜索   │ │ Tavily搜索   │ │ Tavily搜索   │  │
│  │ 数据收集     │ │ 数据收集     │ │ 数据收集     │ │ 数据收集     │  │
│  └──────┬───────┘ └──────┬───────┘ └──────┬───────┘ └──────┬───────┘  │
│         │                │                │                │           │
│         └────────────────┴────────────────┴────────────────┘           │
│                                ↓ 汇总                                   │
│                    ┌───────────────────────┐                            │
│                    │ 📋 Shared State Store │ ← 消息总线（文件系统）      │
│                    │ (/workspace/agent_state/)                         │
│                    └───────────────┬───────┘                            │
│                                    ↓                                    │
│                    ┌──────────────────────────────────┐                │
│                    │ ✏️  Generation Agent (生成Agent) │                │
│                    │  职责: 综合Research结果生成任务   │                │
│                    │  模型: qwen3.6-plus               │                │
│                    └──────────────────┬───────────────┘                │
│                                       ↓                                │
│                    ┌──────────────────────────────────┐                │
│                    │ 🔎  Review Agent (审核Agent)     │                │
│                    │  职责: 去重、质量评估、合并、优化 │                │
│                    │  模型: qwen3.6-plus               │                │
│                    └──────────────────┬───────────────┘                │
│                                       ↓                                │
│                    ┌──────────────────────────────────┐                │
│                    │ ⚡ Execution Agent (执行Agent)   │                │
│                    │  职责: 看板写入、进度跟踪、状态同步│                │
│                    │  方式: KanbanClient (Python)      │                │
│                    └──────────────────┬───────────────┘                │
│                                       ↓                                │
│                    ┌──────────────────────────────────┐                │
│                    │  📊 Observability Collector      │                │
│                    │  职责: 状态采集、指标计算、日志汇总│                │
│                    └──────────────────┬───────────────┘                │
│                                       ↓                                │
│              ┌─────────────────────────────────────────────────┐       │
│              │              Kanban RDS Database                │       │
│              └─────────────────────────────────────────────────┘       │
└────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Agent角色详细定义

#### 2.2.1 🎯 Orchestrator Agent（规划Agent）

| 属性 | 定义 |
|------|------|
| **角色** | 系统大脑，负责任务编排和生命周期管理 |
| **核心职责** | 1. 查询看板数据库，分析T1-T7各目标状态<br>2. 识别目标差距（阶段/瓶颈/缺失行动）<br>3. 制定Research策略（为每个Research Agent分配查询）<br>4. 监控整体流程，处理异常<br>5. 决定是否触发新一轮任务生成 |
| **模型** | qwen3.6-plus（高推理能力） |
| **输入** | 看板数据库状态 + 7大目标定义 + 历史任务统计 |
| **输出** | Research任务分配列表 + 优先级排序 |
| **触发条件** | Scheduler检测到 pending < 10 |
| **执行方式** | 主Session内执行（不spawn，保证控制权） |
| **超时限制** | 10分钟 |

**工作流程**：
```
1. 查询看板 → 获取所有pending/completed任务
2. 目标差距分析 → T1-T7 各维度评分
3. 生成Research策略 → {domain: [queries]}
4. 启动Research Agents → 并行spawn
5. 等待完成 → 监控进度
6. 触发Generation → 汇总所有Research结果
7. 触发Review → 审核生成结果
8. 触发Execution → 写入看板
9. 周期结束 → 记录执行报告
```

#### 2.2.2 🔍 Research Agent（研究Agent）

| 属性 | 定义 |
|------|------|
| **角色** | 领域专家，负责深度信息收集 |
| **核心职责** | 1. 接收Orchestrator分配的Research查询<br>2. 使用Tavily Search执行深度搜索<br>3. 分析搜索结果，提取关键发现和行动建议<br>4. 输出结构化Research报告 |
| **模型** | qwen3.6-plus（高推理能力） |
| **输入** | Research查询列表（2-5个/Agent） |
| **输出** | 结构化Research报告（JSON格式） |
| **执行方式** | spawn独立子代理（并行执行） |
| **超时限制** | 15分钟 |

**Research Agent分组**：

| Agent | 负责领域 | 典型查询方向 |
|-------|---------|-------------|
| Research #1 | T1 AI助手 + T2 商业 | AI agent架构、商业化模式、竞品分析 |
| Research #2 | T3 学术 + T4 财富 | 学术前沿、投资策略、量化工具 |
| Research #3 | T5 家庭 + T6 社会 | 教育规划、政策动态、社会参与 |
| Research #4 | T7 健康 + 跨领域 | 健康科技、跨领域创新 |

**Research报告格式（JSON）**：
```json
{
  "agent_id": "research_1",
  "domain": "T1-T2",
  "timestamp": "2026-04-20T02:30:00+08:00",
  "queries": [
    {
      "query": "multi-agent LLM orchestration patterns 2026",
      "results_count": 8,
      "key_findings": ["...", "..."],
      "action_suggestions": ["...", "..."]
    }
  ],
  "summary": "综合发现...",
  "recommended_tasks": [
    {
      "title": "T1: 优化多Agent协作机制",
      "description": "基于Research发现...",
      "priority": 2,
      "confidence": 0.85
    }
  ]
}
```

#### 2.2.3 ✏️ Generation Agent（生成Agent）

| 属性 | 定义 |
|------|------|
| **角色** | 任务设计师，将Research转化为可执行任务 |
| **核心职责** | 1. 汇总所有Research Agent报告<br>2. 综合交叉分析，识别高价值任务机会<br>3. 生成具体可执行的看板任务<br>4. 确保任务描述包含充分上下文 |
| **模型** | qwen3.6-plus |
| **输入** | 所有Research Agent的JSON报告 + 当前看板状态 |
| **输出** | 候选任务列表（5-15个） |
| **执行方式** | spawn独立子代理 |
| **超时限制** | 10分钟 |

#### 2.2.4 🔎 Review Agent（审核Agent）

| 属性 | 定义 |
|------|------|
| **角色** | 质量守门员，确保任务质量 |
| **核心职责** | 1. 与现有pending任务去重（语义匹配+标题相似度）<br>2. 评估任务质量（具体性/可执行性/优先级合理性）<br>3. 合并相似任务<br>4. 输出最终任务列表 |
| **模型** | qwen3.6-plus |
| **输入** | Generation输出的候选任务 + 看板pending任务列表 |
| **输出** | 审核通过的任务列表 + 审核报告 |
| **执行方式** | 主Session内执行（可直读看板） |
| **超时限制** | 5分钟 |

**去重策略**：
```python
def deduplicate(candidate_tasks, existing_pending_tasks):
    """
    多维度去重：
    1. 精确标题匹配 → 直接跳过
    2. 语义相似度（LLM判断）→ 相似度 > 0.8 跳过
    3. 关键词重叠率 → > 70% 且目标相同 → 合并
    4. 48h内标题前20字 → 传统去重兜底
    """
    pass
```

#### 2.2.5 ⚡ Execution Agent（执行Agent）

| 属性 | 定义 |
|------|------|
| **角色** | 执行者，负责任务写入和状态同步 |
| **核心职责** | 1. 将审核通过的任务写入看板数据库<br>2. 设置正确状态（pending）、类型（auto_generated_v4.4）<br>3. 更新任务计数和统计<br>4. 记录执行日志 |
| **实现方式** | KanbanClient Python类（非LLM，确定性执行） |
| **输入** | 审核通过的任务列表 |
| **输出** | 执行结果报告（成功/失败/重试） |
| **重试策略** | 最多3次，指数退避（5s/10s/20s） |

### 2.3 Agent通信协议

#### 2.3.1 通信方式：文件系统 + 共享状态

```
/workspace/agent_state/
├── orchestrator/
│   ├── gap_analysis.json          # 目标差距分析结果
│   ├── research_assignment.json   # Research任务分配
│   └── cycle_report.json          # 本轮执行报告
├── research/
│   ├── research_1.json            # Research Agent #1 报告
│   ├── research_2.json            # Research Agent #2 报告
│   ├── research_3.json            # Research Agent #3 报告
│   └── research_4.json            # Research Agent #4 报告
├── generation/
│   ├── candidate_tasks.json       # Generation输出
│   └── generation_log.md          # 生成过程日志
├── review/
│   ├── reviewed_tasks.json        # 审核通过的任务
│   └── review_report.md           # 审核报告
├── execution/
│   ├── execution_result.json      # 执行结果
│   └── execution_log.md           # 执行日志
└── observability/
    ├── cycle_metrics.json         # 本轮指标
    └── history/
        └── YYYY-MM-DD_HH-MM.json  # 历史周期记录
```

#### 2.3.2 状态机

```
IDLE → ORCHESTRATING → RESEARCHING → GENERATING → REVIEWING → EXECUTING → COMPLETE
  ↑                                                                                    │
  └─────────────────────────────（错误/重试）──────────────────────────────────────────┘
```

| 状态 | 转换条件 | 超时 |
|------|---------|------|
| IDLE | pending < 10，触发新周期 | 无 |
| ORCHESTRATING | Orchestrator开始分析 | 10分钟 |
| RESEARCHING | 所有Research Agent已启动 | 20分钟 |
| GENERATING | 所有Research完成（≥3/4） | 10分钟 |
| REVIEWING | Generation完成 | 5分钟 |
| EXECUTING | Review完成 | 3分钟 |
| COMPLETE | 所有任务写入完成 | 无 |

#### 2.3.3 错误处理

```python
ERROR_HANDLING = {
    'research_timeout': '等待其他Research完成，跳过超时Agent',
    'research_failure': '重试1次，仍失败则跳过',
    'generation_failure': '使用已有Research结果直接生成（降级模式）',
    'review_failure': '跳过审核，直接写入（标记为unreviewed）',
    'execution_failure': '指数退避重试（5s/10s/20s），最终记录失败',
    'orchestrator_failure': '整个周期终止，记录错误报告，等待下一周期',
}
```

---

## 三、版本演进路线

### 3.1 版本矩阵

| 版本 | 架构 | 任务生成方式 | 状态 |
|------|------|-------------|------|
| V4.0 | 单Agent | Python规则模板 | 已废弃 |
| V4.1 | 单Agent | LLM关键词匹配 | 已废弃 |
| V4.2 | 单Agent | LLM全栈推理 | **当前运行** |
| **V4.3** | **2-Agent** | **LLM分析 + LLM生成** | **下一步** |
| **V4.4** | **5-Agent** | **Orchestrator + Research×4 + Generation + Review + Execution** | **目标架构** |

### 3.2 迁移路径

```
V4.2 (当前) ──→ V4.3 (过渡) ──→ V4.4 (目标)
   │                │               │
   │                │               │
   │  1周           │  2-3周        │  4-6周
   │                │               │
   └────────────────┴───────────────┘
```

### 3.3 V4.3（过渡版本）— 2-Agent分离

**核心变化**：将V4.2的"分析+生成"拆分为两个Agent

```
Orchestrator/Analysis Agent ──→ Generation Agent
(差距分析 + Research策略)        (任务生成 + 去重 + 写入)
```

**为什么先做V4.3**：
1. 风险更低：只拆分一个环节，保持简单
2. 验证多Agent通信协议
3. 为V4.4积累实践经验
4. 可以先解决最关键的痛点（单Agent上下文过长）

### 3.4 旧版本清理

```bash
# 保留（当前使用）
scripts/self-driving-scheduler-v4.2.py
skills/self-driving-scheduler-skill/execute/task_generator_v4_2.py

# 标记废弃（保留归档）
skills/self-driving-scheduler-skill/execute/task_generator.py         # V4.0
skills/self-driving-scheduler-skill/execute/task_generator_v3.py      # V4.1
skills/self-driving-scheduler-skill/execute/task_generator_v4.py      # V4.x

# 新建（V4.4）
scripts/self-driving-scheduler-v4.4.py
skills/self-driving-scheduler-skill/execute/
├── orchestrator.py
├── research_agent.py
├── generation_agent.py
├── review_agent.py
└── execution_agent.py
```

---

## 四、部署方案

### 4.1 推荐方案：混合部署

```
┌─────────────────────────────────────────────┐
│         macOS (mettlyz的Mac mini)           │
│                                             │
│  ┌───────────────────────────────────────┐  │
│  │  OpenClaw Gateway                     │  │
│  │  ├── Scheduler V4.4 (Python)          │  │
│  │  ├── Orchestrator Agent (主Session)    │  │
│  │  ├── Generation Agent (spawn子代理)    │  │
│  │  └── Review Agent (主Session)          │  │
│  └───────────────────────────────────────┘  │
│                    │ spawn                  │
│  ┌───────────────────────────────────────┐  │
│  │  Research Agents (子代理，并行4个)     │  │
│  │  └── Tavily Search (本地脚本)         │  │
│  └───────────────────────────────────────┘  │
│                    │ 写入                   │
│  ┌───────────────────────────────────────┐  │
│  │  Execution Agent (KanbanClient)       │  │
│  │  └── SSH → Server 1 RDS               │  │
│  └───────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
```

**为什么选混合部署**：
- Research需要并行，spawn子代理天然支持
- Orchestrator需要主Session控制力
- Execution需要数据库直连，本地Python最优
- 无需额外基础设施

### 4.2 launchd服务配置

```xml
<!-- ~/Library/LaunchAgents/com.helight.selfdriving.v4.4.plist -->
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.helight.selfdriving.v4.4</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/Resources/Python.app/Contents/MacOS/Python</string>
        <string>/Users/mettlyz/.openclaw/workspace/scripts/self-driving-scheduler-v4.4.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/Users/mettlyz/.openclaw/workspace</string>
    <key>StandardOutPath</key>
    <string>/Users/mettlyz/.openclaw/workspace/logs/self-driving-v4.4.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/mettlyz/.openclaw/workspace/logs/self-driving-v4.4.err</string>
    <key>KeepAlive</key>
    <true/>
    <key>RunAtLoad</key>
    <true/>
    <key>ProcessType</key>
    <string>Background</string>
</dict>
</plist>
```

---

## 五、可观测性方案

### 5.1 指标体系

| 指标类别 | 具体指标 | 采集方式 |
|---------|---------|---------|
| **调度指标** | 周期数、周期耗时、触发次数 | Scheduler内置计数 |
| **Agent指标** | 各Agent启动次数、成功率、平均耗时、失败原因 | 状态文件记录 |
| **任务指标** | 生成任务数、审核通过率、去重率、实际执行数 | Execution结果 |
| **Research指标** | 查询数、结果数、Agent覆盖率 | Research报告 |
| **质量指标** | 任务被采纳率（completed/生成）、平均优先级 | 看板统计 |
| **成本指标** | API调用次数、Token消耗（估算）、子代理spawn数 | OpenClaw日志 |

### 5.2 监控Dashboard方案

#### 方案A：看板内嵌（推荐，零额外成本）

在现有看板系统增加「自我驱动系统监控」页面：

```
前端: React组件读取状态文件 → 渲染Dashboard
后端: Python Flask API读取 /workspace/agent_state/observability/
数据源: JSON文件（周期指标记录）
```

**Dashboard布局**：
```
┌─────────────────────────────────────────────────────────────┐
│  🚀 自我驱动系统 V4.4 监控面板                                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────┐          │
│  │ 总周期数     │ │ 生成任务数   │ │ 审核通过率   │          │
│  │   1,247     │ │    3,842    │ │    87.3%    │          │
│  └─────────────┘ └─────────────┘ └─────────────┘          │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  最近24h周期执行时间线                                │   │
│  │  ██░░██░███░██░░████░░░██░███░██░░░░                 │   │
│  │  00  04  08  12  16  20                              │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────┐  ┌─────────────────┐                  │
│  │ Agent成功率      │  │ 各目标任务分布   │                  │
│  │ Orchestrator 99% │  │ T1 ████████ 32% │                  │
│  │ Research   94%   │  │ T2 ██████  24%  │                  │
│  │ Generation 97%   │  │ T3 ████    16%  │                  │
│  │ Review     96%   │  │ T4 ██      8%   │                  │
│  │ Execution  99%   │  │ T5 ███     12%  │                  │
│  └─────────────────┘  └─────────────────┘                  │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  最近错误                                            │   │
│  │  02:15 Research Agent #3 timeout (T7领域)            │   │
│  │  01:45 Execution retry (connection timeout)          │   │
│  └─────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

#### 方案B：Telegram通知（辅助告警）

关键事件自动推送Telegram：
- 连续3个周期失败
- Research覆盖率 < 50%
- 审核通过率 < 70%
- 新任务生成数 > 20（异常激增）

### 5.3 结构化日志格式

```json
{
  "timestamp": "2026-04-20T02:30:00+08:00",
  "cycle_id": 1248,
  "phase": "RESEARCHING",
  "agent": "research_2",
  "action": "tavily_search",
  "query": "AI材料研发最新进展 2026",
  "result_count": 8,
  "duration_ms": 3200,
  "status": "success"
}
```

---

## 六、实施计划

### Phase 1: V4.3 过渡版本（1周）

| 步骤 | 任务 | 耗时 | 状态 |
|------|------|------|------|
| 1.1 | 创建 orchestrator.py（分析+策略） | 2h | ⬜ |
| 1.2 | 创建 generation_agent.py（生成+去重+写入） | 3h | ⬜ |
| 1.3 | 定义 Agent 通信协议（文件系统） | 1h | ⬜ |
| 1.4 | 编写 V4.3 调度器 | 2h | ⬜ |
| 1.5 | 集成测试 | 2h | ⬜ |
| 1.6 | 部署并运行 | 1h | ⬜ |

### Phase 2: Research Agent 并行化（1-2周）

| 步骤 | 任务 | 耗时 | 状态 |
|------|------|------|------|
| 2.1 | 拆分 research_agent.py（独立可spawn） | 2h | ⬜ |
| 2.2 | 实现4个Research Agent并行调度 | 2h | ⬜ |
| 2.3 | Research结果汇总机制 | 1h | ⬜ |
| 2.4 | 错误处理和降级策略 | 2h | ⬜ |
| 2.5 | 测试和部署 | 2h | ⬜ |

### Phase 3: Review Agent + 可观测性（1-2周）

| 步骤 | 任务 | 耗时 | 状态 |
|------|------|------|------|
| 3.1 | 创建 review_agent.py（去重+质量评估） | 3h | ⬜ |
| 3.2 | 实现多维度去重算法 | 2h | ⬜ |
| 3.3 | 创建 observability collector | 2h | ⬜ |
| 3.4 | 看板Dashboard前端 | 4h | ⬜ |
| 3.5 | Telegram告警集成 | 1h | ⬜ |
| 3.6 | 全链路测试 | 3h | ⬜ |

### Phase 4: V4.4 全量上线 + V4.2 退役（1周）

| 步骤 | 任务 | 耗时 | 状态 |
|------|------|------|------|
| 4.1 | V4.4 全功能集成测试 | 3h | ⬜ |
| 4.2 | 并行运行 V4.2 + V4.4（对比期3天） | - | ⬜ |
| 4.3 | 验证V4.4质量优于V4.2 | 2h | ⬜ |
| 4.4 | 停止V4.2调度器 | 30min | ⬜ |
| 4.5 | 更新文档和memory记录 | 1h | ⬜ |

---

## 七、风险与缓解

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|---------|
| Agent spawn过多导致Gateway超时 | 高 | 中 | 限制并发≤4，间隔启动 |
| Research结果质量不佳 | 中 | 低 | 降级模式、Tavily参数优化 |
| 数据库写入冲突 | 中 | 低 | 事务保护、重试机制 |
| 旧版本任务生成器仍运行 | 低 | 中 | 清理V4.0-V4.1，停用V4.2 |
| 状态文件丢失/损坏 | 中 | 低 | JSON校验、备份机制 |
| 成本超支（Token消耗） | 低 | 低 | 周期频率限制、Agent超时控制 |

---

## 八、关键设计决策记录

| 决策 | 选项A | 选项B | 选择 | 理由 |
|------|-------|-------|------|------|
| 通信方式 | 消息队列(Redis) | 文件系统(JSON) | **文件系统** | 零依赖，已有基础设施 |
| Research并行度 | 2个Agent | 4个Agent | **4个Agent** | 覆盖7大目标，充分利用并行 |
| 审核位置 | 独立Agent | 集成在Generation | **独立Agent** | 关注点分离，质量保障 |
| 部署模式 | 全云端 | 混合（本地+RDS） | **混合部署** | 利用OpenClaw spawn能力 |
| 演进策略 | 直接V4.4 | V4.3过渡 | **V4.3过渡** | 降低风险，逐步验证 |
| 监控方案 | Grafana | 看板内嵌 | **看板内嵌** | 零额外成本，统一管理 |

---

## 九、文件清单

### 新增文件

| 文件 | 用途 | 阶段 |
|------|------|------|
| `scripts/self-driving-scheduler-v4.3.py` | V4.3调度器 | Phase 1 |
| `scripts/self-driving-scheduler-v4.4.py` | V4.4调度器 | Phase 3 |
| `skills/self-driving-scheduler-skill/execute/orchestrator.py` | 规划Agent | Phase 1 |
| `skills/self-driving-scheduler-skill/execute/research_agent.py` | 研究Agent | Phase 2 |
| `skills/self-driving-scheduler-skill/execute/generation_agent.py` | 生成Agent | Phase 1 |
| `skills/self-driving-scheduler-skill/execute/review_agent.py` | 审核Agent | Phase 3 |
| `skills/self-driving-scheduler-skill/execute/execution_agent.py` | 执行Agent | Phase 3 |
| `skills/self-driving-scheduler-skill/execute/observability.py` | 可观测性收集器 | Phase 3 |
| `output/task-1567/multi-agent-architecture-design.md` | 本文档 | ✅ 完成 |

### 修改文件

| 文件 | 修改内容 | 阶段 |
|------|---------|------|
| `config/self-driving-config.md` | 新增V4.3/V4.4配置说明 | Phase 1 |
| `scripts/self-driving-scheduler-v4.2.py` | 标记废弃 | Phase 4 |

---

*文档版本: V1.0 | 创建日期: 2026-04-20 | 下次评审: V4.3部署后*
