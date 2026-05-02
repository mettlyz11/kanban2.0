# Self-Improving AI Agent 架构文档

**项目**: T1 - AI助手优化与能力提升  
**日期**: 2026-04-25  
**版本**: v1.0

---

## 一、架构概览

```
┌─────────────────────────────────────────────────────┐
│              Self-Improvement Loop                   │
│                                                      │
│  ┌──────────────┐   ┌──────────────┐                │
│  │  Quality     │   │  Error       │                │
│  │  Evaluator   │──▶│  Classifier  │                │
│  └──────────────┘   └──────┬───────┘                │
│         ▲                  │ auto_correct()          │
│         │                  ▼                         │
│  ┌──────────────┐   ┌──────────────┐                │
│  │  DB (tasks)  │◀──│  Best Practice│               │
│  │  attachments │   │  Extractor   │                │
│  └──────────────┘   └──────────────┘                │
└─────────────────────────────────────────────────────┘
```

---

## 二、核心模块说明

### 2.1 ExecutionQualityEvaluator（质量评估器）

**职责**: 对任务的 `execution_log` 和 `result_summary` 进行多维度评分（0-100分）。

**评分维度**:
| 维度 | 权重 | 说明 |
|------|------|------|
| 长度达标 | 40分 | execution_log ≥ 200字，result_summary ≥ 50字 |
| 关键词覆盖 | 40分 | 工具使用、执行过程、问题解决、产出描述四组关键词 |
| 结构完整性 | 20分 | 段落数量 ≥ 3，存在编号/条目列表 |

**达标标准**: 综合分 ≥ 60 且长度均满足硬性门槛

### 2.2 ErrorClassifier（错误分类器）

**识别的错误类型**:
- `LOW_QUALITY`: execution_log/result_summary 质量分低于阈值
- `EMPTY_OUTPUT`: 任务有产出但附件表中无记录
- `DUPLICATE`: 标题相似度过高的重复任务
- `STALE`: 长时间停留在 in_progress 状态（≥48小时）

**自动修正策略**:
- HIGH severity 错误 → 将 completed 状态重置为 pending，触发重新执行
- MEDIUM severity → 记录到改进报告，人工介入

### 2.3 BestPracticeExtractor（最佳实践提取器）

**工作流程**:
1. 查询近期 completed 任务，过滤质量分 ≥ 80 的记录
2. 提取每个任务的执行模式（前3句 + 关键动词短语）
3. 按 task_type 分组，生成可复用模板
4. 输出 JSON 格式最佳实践库，供新任务生成参考

### 2.4 SelfImprovementLoop（主循环控制器）

**执行流程**:
```
扫描最近N个任务
    ↓
并行质量评估（ExecutionQualityEvaluator）
    ↓
错误分类 + 自动修正（ErrorClassifier）
    ↓
重复任务检测
    ↓
最佳实践提取（BestPracticeExtractor）
    ↓
生成改进报告（JSON）
```

---

## 三、数据库依赖

| 表名 | 使用字段 | 操作 |
|------|---------|------|
| `tasks` | id, title, status, execution_log, result_summary, task_summary, task_type, updated_at | READ + UPDATE |
| `attachments` | entity_type, entity_id, filename | READ |

---

## 四、输出产物

| 文件 | 说明 |
|------|------|
| `best_practices.json` | 高质量任务的执行模式库 |
| `improvement_report_YYYYMMDD_HHMMSS.json` | 每次运行的完整评估报告 |

---

## 五、部署与集成

```bash
# 单次运行
cd /Users/mettlyz/.openclaw/workspace/scripts
python3 ../output/task-1911/self_improvement_loop.py

# 建议通过 cron 每日运行一次
# openclaw cron add "0 3 * * *" "python3 .../self_improvement_loop.py"
```

---

## 六、扩展方向（2026 Self-Improving Agent 路线图）

1. **多Agent协作评估**: 引入评估Agent与执行Agent分离，评估更客观
2. **向量相似度去重**: 用 embedding 替代字符串匹配检测语义重复任务
3. **强化学习信号**: 将质量分作为奖励信号，微调任务生成策略
4. **实时流式评估**: 执行过程中实时计算质量分，不合格时提前终止

---

## 七、技术栈

- **Python 3.11+** - 核心实现语言
- **pymysql** - 数据库连接（通过 `lib.db_connector` 统一管理）
- **hashlib / re / json** - 标准库工具
- **设计模式**: 职责分离（单一职责）、策略模式（评分策略可替换）
