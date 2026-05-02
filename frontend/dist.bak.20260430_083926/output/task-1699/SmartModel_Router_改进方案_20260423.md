# SmartModel Router 改进方案

**日期**: 2026-04-23
**任务**: #1699 - 需求分析与改进方案

---

## 一、关键问题汇总

### P0 - 阻断性问题
1. **aliyun 欠费在 Fallback 链中**: 第 4 级，每次降级都增加延迟
2. **Memory Search 失效**: OpenAI Embeddings 配额已耗尽，影响所有语义搜索功能
3. **硬编码 API Key**: `auto_task_scheduler_v2.py` 包含明文 Dashscope API Key

### P1 - 严重问题
1. **Fallback 链冗余**: `alicodingplan/qwen3.6-plus` 出现 2 次
2. **缺少健康检查**: 无 Provider 存活探测
3. **序列降级延迟**: 失败后逐级降级，累计约 30-50s

### P2 - 改进项
1. **任务类型路由**: 未按场景选择模型
2. **成本管理**: cost 字段未用于路由决策
3. **无并发降级**: 可同时尝试多个后备模型

---

## 二、实施方案

### 2.1 立即修复（配置文件变更）

**目标**: 修改 `openclaw.json` 中的 Fallback 链

```
优化后的 Fallback 链 (9级):

1. alicodingplan/kimi-k2.5
2. huoshanCoding/ark-code-latest
3. dmxapi/kimi-k2.5-free
4. moonshot/kimi-k2.6          ← 原 aliyun 提升至此
5. huoshanCoding/doubao-seed-2.0-pro  ← 加入更强的豆包
6. huoshan/doubao-seed-2-0-pro-260215
7. deepseek/deepseek-chat
8. dmxapi/gpt-5.4
9. dmxapi/claude-sonnet-4-6     ← aliyun 移出
```

变更要点：
- **移除 aliyun/qwen3.6-plus**（欠费）
- **移除重复的 alicodingplan/qwen3.6-plus**
- **moonshot/kimi-k2.6 提升到第 4 位**
- 保持核心降级路径不变

### 2.2 Memory Search 修复

```python
# 方案 A: 切换至 huoshan 嵌入模型（已有 API Key）
memorySearch.remote.baseUrl → https://ark.cn-beijing.volces.com/api/coding/v3
memorySearch.provider → huoshan
memorySearch.model → doubao-embedding-text-250515

# 方案 B: 添加本地 fallback（基于关键词匹配）
memorySearch.fallback → "keyword"
```

推荐方案 A + B 结合。

### 2.3 并发降级策略

当前：`for each fallback: try → fail → next` (序列)
改进：`try top-3 in parallel → use first success` (并发)

```
┌──────────┐
│ primary  │─── 单次尝试 3s 超时
└────┬─────┘
     │ 失败
     ▼
┌─────────────────────┐
│ parallel group 1    │  ← 同时尝试 fallback 1,2,3
│ (kimi-k2.5, ark,   │     第一个成功即返回
│  kimi-k2.5-free)   │     超时 5s
└─────────────────────┘
     │ 全失败
     ▼
┌─────────────────────┐
│ parallel group 2    │  ← 同时尝试 fallback 4,5,6
│ (kimi-k2.6, doubao,│
│  deepseek)          │
└─────────────────────┘
     │ 全失败
     ▼
┌─────────────────────┐
│ final group         │  ← gpt-5.4, claude-sonnet-4-6
│ (高成本模型兜底)     │
└─────────────────────┘
```

预计降级延迟从 **30-50s 降至 5-10s**。

---

## 三、任务调度器安全修复

### 3.1 需清理的硬编码 API Key

| 文件 | 行内容 | 修复方式 |
|------|--------|---------|
| `auto_task_scheduler_v2.py` | `LLM_API_KEY = "sk-c7c60720621149d8adf20adf17c9dc81"` | 改为 `os.environ.get('ALIYUN_API_KEY')` |
| `auto_task_scheduler_v2_enhanced.py` | 类似硬编码 | 同上 |
| `auto_task_scheduler_v3_strategic.py` | 类似硬编码 | 同上 |

### 3.2 调度器统一

建议将 4 个调度器脚本合并为单一 `task-scheduler.py`，使用配置模式区分运行策略：
- `--mode strategic` (V3 战略模式)
- `--mode enhanced` (V2 增强模式)
- `--mode daemon` (守护进程模式)

---

## 四、优先级路由矩阵

按任务类型自动选择模型：

| 任务类型 | 推荐模型 | 原因 |
|---------|---------|------|
| 代码生成 | huoshanCoding/ark-code-latest | 代码专项模型 |
| 推理分析 | deepseek/deepseek-reasoner | 推理能力强 |
| 创意写作 | dmxapi/claude-sonnet-4-6 | 文笔最佳 |
| 日常对话 | alicodingplan/kimi-k2.5 | 速度快 |
| API 调用 | moonshot/kimi-k2.6 | 稳定可靠 |

---

## 五、成本优化建议

1. **优先使用免费/低价模型**: kimi-k2.5-free 作为首级降级
2. **缓存重复请求**: 对相同 prompt 的常见查询缓存结果
3. **模型按需分级**: 
   - Tier 1 (日常): kimi-k2.5, ark-code-latest, doubao-seed-2.0-pro
   - Tier 2 (重要): kimi-k2.6, deepseek-chat, gpt-5.4
   - Tier 3 (关键): claude-sonnet-4-6 (仅保底)

---

## 六、监控建议

需要跟踪的关键指标：
1. **降级率**: 每次调用的 Fallback 层级
2. **失败率**: 每个 Provider 的失败请求比例
3. **响应时间**: P50/P95/P99 延迟
4. **成本**: 每次调用的实际成本（如果 cost 字段正确配置）
5. **限频率**: 429 错误的发生频率
