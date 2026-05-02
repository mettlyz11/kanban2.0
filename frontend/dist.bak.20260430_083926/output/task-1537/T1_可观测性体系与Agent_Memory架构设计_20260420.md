# T1: AI助手优化 - 可观测性体系与Agent Memory架构升级

**看板任务**: #1537  
**日期**: 2026-04-20  
**状态**: ✅ 设计完成（待批准执行）  
**类型**: 架构设计文档

---

## 一、现状诊断

### 1.1 当前可观测性体系

| 维度 | 当前状态 | 问题 |
|------|----------|------|
| **Token消耗** | 无记录 | 无法追踪各模型/任务的token成本 |
| **Subagent追踪** | 仅kanban.last_heartbeat | 无生命周期全链路追踪 |
| **错误分析** | Gateway日志散乱 | 无结构化错误分类与统计 |
| **成本监控** | 无 | 无告警机制，无法发现异常消耗 |
| **性能指标** | 无 | 无响应时间/成功率/质量评分 |

### 1.2 当前Memory架构

```
┌─────────────────────────────────────────────────┐
│              当前Memory架构（扁平化）              │
├─────────────────────────────────────────────────┤
│  memory/                                        │
│  ├── 2026-04-20.md        ← 每日笔记（45个）     │
│  ├── 2026-04-19.md        ← 每日笔记            │
│  ├── ...                                       │
│  ├── MEMORY.md            ← 长期记忆（单文件）    │
│  └── .dreams/             ← OpenClaw内置         │
│      ├── events.jsonl     ← 召回事件(165条)      │
│      └── short-term-recall.json ← 短期召回(157)  │
└─────────────────────────────────────────────────┘
```

**问题**：
- ❌ 无语义关联（文件间无结构化链接）
- ❌ 召回仅基于文本匹配，无概念图谱
- ❌ MEMORY.md单文件膨胀，查询效率下降
- ❌ 无记忆衰减机制，重要/不重要信息同等权重
- ❌ 无法支持跨session深度推理

### 1.3 数据源现状

| 数据源 | 位置 | 大小 | 可用性 |
|--------|------|------|--------|
| Gateway日志 | `/tmp/openclaw/*.log` | ~44MB/3天 | ✅ JSON格式 |
| 记忆文件 | `memory/*.md` | 860KB/61文件 | ✅ 结构化 |
| 看板数据库 | RDS MySQL | ~1282任务 | ✅ 可查询 |
| Dreams事件 | `memory/.dreams/events.jsonl` | 59KB/165条 | ✅ JSONL |
| Cron配置 | `~/.openclaw/cron/jobs.json` | 81KB | ✅ JSON |

---

## 二、可观测性体系设计

### 2.1 整体架构

```
┌──────────────────────────────────────────────────────────────┐
│                    OpenClaw 可观测性体系                       │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌────────────────────┐   │
│  │  Token监控   │  │ Subagent追踪 │  │   错误分析引擎      │   │
│  │  Collector  │  │  Lifecycle  │  │   Error Analyzer   │   │
│  └──────┬──────┘  └──────┬──────┘  └────────┬───────────┘   │
│         │               │                   │               │
│         ▼               ▼                   ▼               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │              统一观测数据层 (SQLite)                  │    │
│  │        ~/.openclaw/observability/metrics.db          │    │
│  └──────────────────────┬──────────────────────────────┘    │
│                         │                                    │
│         ┌───────────────┼───────────────┐                   │
│         ▼               ▼               ▼                   │
│  ┌─────────────┐  ┌─────────────┐  ┌────────────────────┐   │
│  │  成本Dashboard│  │  健康Dashboard│  │   告警引擎          │   │
│  │  Cost Panel │  │ Health Panel │  │   Alert Engine     │   │
│  └─────────────┘  └─────────────┘  └────────────────────┘   │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### 2.2 Token消耗监控系统

#### 2.2.1 数据采集方案

由于OpenClaw不直接暴露token API，采用**Gateway日志解析**方案：

```python
# observability/token_collector.py
class TokenCollector:
    """从Gateway日志提取token和成本数据"""
    
    LOG_PATTERNS = {
        'model_usage': r'"model":"([^"]+)"',
        'session_id': r'"sessionId":"([^"]+)"',
        'tool_calls': r'"tool":"([^"]+)"',
        'error': r'"logLevelName":"(ERROR|WARN)"',
    }
    
    MODEL_COSTS = {
        'alicodingplan/qwen3.6-plus': {'input': 0.004, 'output': 0.016},  # 元/千token
        'alicodingplan/kimi-k2.5': {'input': 0.006, 'output': 0.024},
        'alicodingplan/glm-5': {'input': 0.005, 'output': 0.020},
        # ... 其他模型
    }
```

#### 2.2.2 数据模型

```sql
-- metrics.db schema
CREATE TABLE token_usage (
    id INTEGER PRIMARY KEY,
    timestamp TEXT NOT NULL,
    session_key TEXT,
    model TEXT NOT NULL,
    input_tokens INTEGER,
    output_tokens INTEGER,
    total_tokens INTEGER,
    cost_usd REAL,
    task_id INTEGER,  -- 关联看板任务
    tool_used TEXT,   -- 触发工具
    source TEXT       -- 来源: telegram/feishu/cron/heartbeat
);

CREATE TABLE daily_cost_summary (
    date TEXT PRIMARY KEY,
    total_cost_usd REAL,
    total_tokens INTEGER,
    model_breakdown TEXT,  -- JSON
    task_breakdown TEXT,   -- JSON
    anomaly_detected INTEGER DEFAULT 0
);

CREATE TABLE subagent_lifecycle (
    id INTEGER PRIMARY KEY,
    task_id INTEGER,
    session_key TEXT,
    spawned_at TEXT,
    completed_at TEXT,
    status TEXT,  -- running/completed/failed/killed
    model_used TEXT,
    tokens_consumed INTEGER,
    cost_usd REAL,
    error_message TEXT,
    heartbeat_count INTEGER
);
```

#### 2.2.3 成本告警规则

| 告警级别 | 触发条件 | 通知方式 |
|---------|---------|---------|
| ⚠️ WARNING | 日成本 > $5 | Telegram消息 |
| 🔴 CRITICAL | 日成本 > $20 | Telegram + 自动降级模型 |
| 🔥 EMERGENCY | 日成本 > $50 | Telegram + 暂停非核心cron |
| 📊 INFO | 单任务成本 > $2 | 任务总结中标注 |

### 2.3 Subagent生命周期追踪

#### 2.3.1 追踪矩阵

```
Subagent Lifecycle States:
  
  PENDING → SPAWNED → RUNNING → [COMPLETED | FAILED | KILLED | TIMEOUT]
                    ↓
              HEARTBEAT (每5分钟)
                    ↓
              [STALL_DETECTED → ALERT]
```

#### 2.3.2 实现方案

**方案A：Gateway日志解析（推荐，立即实施）**
- 从日志中提取spawn/completed/error事件
- 关联kanban DB的subagent_session_key
- 计算生命周期指标

**方案B：Kanban DB增强（中期）**
- 在tasks表增加观测字段
- 每次spawn/complete自动更新
- 支持SQL查询分析

### 2.4 错误分析引擎

#### 2.4.1 错误分类体系

```
错误分类树：
├── 工具错误 (Tool Errors)
│   ├── exec失败 (权限/语法/超时)
│   ├── web_search失败 (API限制/网络)
│   ├── 文件操作失败 (路径/权限)
│   └── 数据库操作失败 (连接/SQL)
├── 模型错误 (Model Errors)
│   ├── 超时
│   ├── 内容过滤
│   └── 模型降级
├── 系统错误 (System Errors)
│   ├── Gateway崩溃
│   ├── 磁盘空间不足
│   └── 内存溢出
└── 业务错误 (Business Errors)
    ├── 任务失败
    ├── 数据不一致
    └── 审核未通过
```

#### 2.4.2 分析指标

| 指标 | 计算方式 | 告警阈值 |
|------|---------|---------|
| 错误率 | 错误次数/总操作次数 | > 10% |
| 高频错误 | 同一错误24h内>5次 | 自动报告 |
| 错误恢复率 | 自动恢复/总错误 | < 50% |
| MTTR | 错误发生→恢复平均时间 | > 30min |

### 2.5 Dashboard实现

#### 2.5.1 命令行Dashboard（立即）

```bash
# 每日报告命令
python3 ~/.openclaw/workspace/scripts/observability/daily_report.py

# 输出示例：
# ═══════════════════════════════════════════
# 📊 OpenClaw 可观测性日报 - 2026-04-20
# ═══════════════════════════════════════════
# 💰 成本: $2.34 (↓12% vs 昨日)
# 🤖 活跃模型: qwen3.6-plus (78%), kimi-k2.5 (22%)
# 📋 任务: 完成12, 失败1, 进行中4
# ⚠️  告警: 1个 (qqbot.token持续失败)
# 🧠 Memory: 45日记, 860KB, 召回165次
# ═══════════════════════════════════════════
```

#### 2.5.2 Web Dashboard（中期）

- 基于SQLite + 轻量Web框架
- 本地访问: `http://localhost:18790/observability`
- 面板：成本趋势、任务完成率、错误热图、Memory质量

---

## 三、Agent Memory架构升级

### 3.1 目标架构（三层Memory System）

```
┌─────────────────────────────────────────────────────────────┐
│                  Agent Memory Architecture v2               │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  L1: Working Memory (实时)                                   │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  • 当前session上下文                                 │   │
│  │  • 短期召回 (OpenClaw .dreams)                       │   │
│  │  • TTL: session生命周期                              │   │
│  └─────────────────────────────────────────────────────┘   │
│                          ↕                                  │
│  L2: Episodic Memory (事件)                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  • 日记文件 (memory/YYYY-MM-DD.md)                   │   │
│  │  • 任务执行记录 (output/task-*)                      │   │
│  │  • 对话摘要 (memory/session-*.md)                    │   │
│  │  • TTL: 90天热存储 + 归档                            │   │
│  └─────────────────────────────────────────────────────┘   │
│                          ↕                                  │
│  L3: Semantic Memory (知识图谱) ← 新增                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  • 概念图谱 (memory/graph/concepts.jsonl)            │   │
│  │  • 实体关系 (memory/graph/entities.jsonl)            │   │
│  │  • 经验规则 (memory/graph/rules.jsonl)               │   │
│  │  • 衰减权重 (memory/graph/weights.json)              │   │
│  │  • TTL: 永久（带衰减）                                │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 语义记忆层（L3）详细设计

#### 3.2.1 概念图谱

```jsonl
// memory/graph/concepts.jsonl
{"id":"observability","label":"可观测性体系","category":"系统架构","tags":["monitoring","cost","dashboard"],"created":"2026-04-20","weight":0.95,"related_tasks":[1537],"source":"task-1537-design"}
{"id":"agent-memory","label":"Agent Memory","category":"AI架构","tags":["memory","recall","graph"],"created":"2026-04-20","weight":0.90,"related_tasks":[1537,1579],"source":"task-1537-design"}
{"id":"t109-hermes","label":"T109 Hermes","category":"产品","tags":["transition-state","quantum-chemistry","SaaS"],"created":"2026-04-19","weight":0.98,"related_tasks":[1568,1573],"source":"task-1573-verification"}
```

#### 3.2.2 实体关系

```jsonl
// memory/graph/entities.jsonl
{"source":"刘宇宙","relation":"创始人","target":"和光智成","confidence":1.0,"evidence":"USER.md","updated":"2026-04-20"}
{"source":"和光智成","relation":"产品","target":"T109","confidence":1.0,"evidence":"USER.md","updated":"2026-04-20"}
{"source":"T109","relation":"子产品","target":"Hermes","confidence":0.9,"evidence":"task-1573","updated":"2026-04-20"}
{"source":"北航","relation":"合作","target":"和光智成","confidence":0.95,"evidence":"USER.md","updated":"2026-04-20"}
```

#### 3.2.3 经验规则

```jsonl
// memory/graph/rules.jsonl
{"id":"R001","condition":"任务涉及Server操作","action":"requires_audit=true","confidence":1.0,"source":"AGENTS.md","hits":12}
{"id":"R002","condition":"用户说'需要'","action":"先评估后执行","confidence":1.0,"source":"SOUL.md","hits":8}
{"id":"R003","condition":"子代理启动","action":"每分钟最多1个","confidence":1.0,"source":"AGENTS.md","hits":25}
{"id":"R004","condition":"Research场景","action":"必须用Tavily Search","confidence":1.0,"source":"AGENTS.md","hits":45}
```

#### 3.2.4 记忆衰减与权重

```json
// memory/graph/weights.json
{
  "decay_rate": 0.01,          // 每日衰减率
  "boost_on_recall": 0.1,      // 每次召回提升
  "boost_on_update": 0.2,      // 每次更新提升
  "min_weight": 0.1,           // 最小权重（不删除）
  "archive_threshold": 0.2,    // 低于此值归档
  "last_cleanup": "2026-04-20"
}
```

### 3.3 Memory操作API

```python
# memory/graph_api.py
class MemoryGraph:
    """语义记忆图操作API"""
    
    def add_concept(self, id, label, category, tags, weight=0.5):
        """添加概念节点"""
        
    def add_relation(self, source, relation, target, confidence=0.8):
        """添加实体关系"""
        
    def add_rule(self, condition, action, confidence=0.9):
        """添加经验规则"""
        
    def search(self, query, top_k=10):
        """语义搜索（概念+关系+规则）"""
        
    def get_related(self, concept_id, depth=2):
        """获取关联子图"""
        
    def decay(self):
        """执行记忆衰减"""
        
    def export_markdown(self):
        """导出为可读格式（兼容现有系统）"""
```

### 3.4 迁移路径

```
Phase 0: 诊断（当前）✅
    ↓
Phase 1: 可观测性基础（本周）
    ├── 1.1 Gateway日志解析器
    ├── 1.2 SQLite metrics数据库
    ├── 1.3 命令行Dashboard
    └── 1.4 成本告警规则
    ↓
Phase 2: Memory图结构（下周）
    ├── 2.1 concepts.jsonl初始化
    ├── 2.2 entities.jsonl初始化（从USER.md/MEMORY.md提取）
    ├── 2.3 rules.jsonl初始化（从AGENTS.md/SOUL.md提取）
    └── 2.4 图搜索API
    ↓
Phase 3: 自动化（2周后）
    ├── 3.1 任务完成自动更新图谱
    ├── 3.2 记忆衰减cron
    ├── 3.3 召回质量分析
    └── 3.4 Web Dashboard
    ↓
Phase 4: 深度集成（1个月后）
    ├── 4.1 跨session推理增强
    ├── 4.2 记忆质量评分
    ├── 4.3 自动概念发现
    └── 4.4 知识蒸馏
```

---

## 四、执行计划与优先级

### 4.1 本周可执行项（Phase 1）

| 序号 | 任务 | 预计时间 | 依赖 | 优先级 |
|------|------|---------|------|--------|
| P1.1 | 创建observability目录结构 | 10min | 无 | P0 |
| P1.2 | Gateway日志解析器 | 30min | P1.1 | P0 |
| P1.3 | SQLite metrics schema | 15min | P1.1 | P0 |
| P1.4 | 日志回填（过去7天） | 20min | P1.2+P1.3 | P1 |
| P1.5 | 命令行Dashboard | 30min | P1.3 | P1 |
| P1.6 | 成本告警规则 | 15min | P1.3 | P2 |

### 4.2 下周执行项（Phase 2）

| 序号 | 任务 | 预计时间 | 依赖 | 优先级 |
|------|------|---------|------|--------|
| P2.1 | Memory图结构初始化 | 45min | 无 | P0 |
| P2.2 | 从现有文件提取实体关系 | 30min | P2.1 | P0 |
| P2.3 | 规则提取（AGENTS.md→rules） | 20min | P2.1 | P1 |
| P2.4 | 图搜索API | 45min | P2.1 | P1 |

---

## 五、预期效果

### 5.1 可观测性提升

| 指标 | 当前 | Phase 1后 | Phase 3后 |
|------|------|-----------|-----------|
| 成本可见性 | ❌ 无 | ✅ 日报 | ✅ 实时 |
| 错误追踪 | ❌ 手动 | ✅ 分类统计 | ✅ 自动告警 |
| Subagent追踪 | ⚠️ 基础 | ✅ 生命周期 | ✅ 全链路 |
| 性能分析 | ❌ 无 | ⚠️ 基础 | ✅ 完整 |

### 5.2 Memory能力提升

| 能力 | 当前 | Phase 2后 | Phase 4后 |
|------|------|-----------|-----------|
| 语义搜索 | ⚠️ 文本匹配 | ✅ 图搜索 | ✅ 推理级 |
| 跨session记忆 | ⚠️ 文件查询 | ✅ 关联查询 | ✅ 自动推理 |
| 记忆衰减 | ❌ 无 | ✅ 权重衰减 | ✅ 智能遗忘 |
| 知识发现 | ❌ 手动 | ⚠️ 手动 | ✅ 自动发现 |

---

## 六、风险评估

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| Gateway日志格式变化 | 解析器失效 | 版本化解析器 + 格式校验 |
| SQLite并发写入 | 数据损坏 | WAL模式 + 写入队列 |
| 记忆图过大 | 搜索变慢 | 定期归档 + 索引优化 |
| 误告警 | 打扰用户 | 可调节阈值 + 静默时段 |

---

## 七、下一步

**⚠️ 需要刘总批准：**

1. **Phase 1立即执行？**（创建可观测性基础 - 约2小时工作量）
2. **Phase 2下周执行？**（Memory图结构初始化 - 约2.5小时）
3. **是否需要在Server 1部署Web Dashboard？**（需要额外配置）

**建议：立即执行Phase 1，本周内完成基础可观测性体系。**
