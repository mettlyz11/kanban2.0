# SmartModel Router 系统架构评审报告

**日期**: 2026-04-23
**任务**: #1699 - 系统架构评审与需求分析
**分析范围**: OpenClaw 模型路由系统、Provider 管理、降级策略、任务调度

---

## 1. 系统概述

SmartModel Router 是 OpenClaw 的核心模型路由基础设施，负责在多个 AI 模型提供商之间进行智能调度和故障转移。系统由以下核心组件构成：

- **核心路由器**: OpenClaw Gateway (端口 18789, local mode)
- **Provider 管理层**: 7 个 Provider，约 45 个可用模型
- **Fallback 链**: 10 级降级策略
- **任务调度器**: 4 个版本 (V2, V2-Enhanced, V3-Strategic, Daemon)
- **Memory Search**: 基于 OpenAI Embeddings 的语义搜索

---

## 2. Provider 分析

### 2.1 当前 Provider 清单

| Provider | Base URL | 模型数 | 状态 |
|----------|----------|--------|------|
| **moonshot** | api.moonshot.cn/v1 | 2 | ✅ 活跃 |
| **alicodingplan** | coding.dashscope.aliyuncs.com/v1 | 9 | ✅ 活跃(主路由) |
| **deepseek** | api.deepseek.com/v1 | 2 | ✅ 活跃 |
| **dmxapi** | dmxapi.cn/v1 | 12 | ✅ 活跃 |
| **huoshanCoding** | ark.cn-beijing.volces.com/api/coding/v3 | 9 | ✅ 活跃 |
| **huoshan** | ark.cn-beijing.volces.com/api/v3 | 1 | ✅ 活跃 |
| **aliyun** | dashscope.aliyuncs.com | 16 | ⚠️ 欠费 |

### 2.2 关键发现

1. **aliyun Provider 欠费**: 排在 Fallback 链第 4 位，一旦触发降级到 aliyun，会导致调用失败并继续降级，增加延迟。
2. **alicodingplan 主路由不明确**: 主模型配置为 `alicodingplan/qwen3.6-plus`，但 Fallback 链第 6 位又以 `alicodingplan/qwen3.6-plus` 出现，存在冗余。
3. **huoshanCoding 和 huoshan 共享相同 API Key**: 但使用不同 API endpoint 和模型集，可能存在管理重叠。

---

## 3. Fallback 链分析

### 3.1 当前 Fallback 链 (10级)

```
1. alicodingplan/kimi-k2.5
2. huoshanCoding/ark-code-latest
3. dmxapi/kimi-k2.5-free
4. aliyun/qwen3.6-plus               ← ❌ 欠费
5. moonshot/kimi-k2.6
6. alicodingplan/qwen3.6-plus        ← ⚠️ 与 primary 模型同
7. huoshan/doubao-seed-2-0-pro-260215
8. deepseek/deepseek-chat
9. dmxapi/gpt-5.4
10. dmxapi/claude-sonnet-4-6
```

### 3.2 性能瓶颈

1. **降级延迟**: 序列式降级，每次失败至少等待 3-5 秒超时，10 级降级可能导致 30-50 秒延迟
2. **冗余项**: 第 1 级 (alicodingplan/kimi-k2.5) 与第 6 级 (alicodingplan/qwen3.6-plus) 属于同一 Provider
3. **缺健康检查**: 没有 Provider 健康探测机制，只有在实际调用失败后才降级
4. **free 模型风险**: 第 3 级 dmxapi/kimi-k2.5-free 使用免费模型，可能不稳定或限频
5. **重量级模型排后**: claude-sonnet-4-6 和 gpt-5.4 排在最后，但延迟高、成本大，实际很少用到

---

## 4. Memory Search 系统分析

### 4.1 当前配置

- **Provider**: openai (embeddings)
- **Fallback**: none (无降级)
- **问题**: 嵌入 API 调用频繁触发 429 限频，导致 memory_search 失效

### 4.2 根因

- 每月配额耗尽，重置时间为 2026-04-23 23:59:59 (CST)
- 远程配置指向 Huoshan API key 但实际使用 OpenAI
- 无本地 fallback 机制（如缓存或基于关键词的搜索）

---

## 5. 任务调度器分析

### 5.1 多版本共存问题

系统中存在 **4 个版本** 的任务调度器：

| 文件 | 用途 | 问题 |
|------|------|------|
| `auto_task_scheduler_v2.py` | 增强版调度 | hardcoded API key |
| `auto_task_scheduler_v2_enhanced.py` | 增强版调度 | 同上 |
| `auto_task_scheduler_v3_strategic.py` | 战略版调度 | 同上 |
| `auto-task-daemon.py` | 守护进程 | 依赖本地队列 |

### 5.2 安全问题

`auto_task_scheduler_v2.py` 中仍存在明文 API Key:
```python
LLM_API_KEY = "sk-c7c60720621149d8adf20adf17c9dc81"
```

这与 TOOLS.md 中 "🔴 NEVER hardcode passwords, API keys, or secrets" 的规则冲突。

---

## 6. 扩展性问题

1. **缺乏 Provider 动态注册**: 所有 Provider 配置在 `openclaw.json` 中静态定义，无法热加载
2. **无负载均衡**: 同一 Provider 的多个模型之间没有基于负载的智能路由
3. **模型能力分级缺失**: 没有按任务类型（推理、编码、创意写作）智能选择模型
4. **成本管理不足**: 多数模型 cost 字段设为 0，无法进行成本优化的路由决策
5. **单点故障**: Fallback 链中有 aliyun/欠费 这样的固定故障点

---

## 7. 改进建议

### 7.1 近期 (1-3 天)

1. **移除 aliyun 降级项**: 将其移出 Fallback 链或放至最后
2. **清理冗余项**: 删除 Fallback 链中的重复项 (`alicodingplan/qwen3.6-plus`)
3. **修复 Memory Search**:
   - 等待配额重置 (今晚)
   - 或将嵌入模型切换至本地/其他 Provider
4. **清理硬编码 API Key**: 在所有调度器脚本中使用 `.env` 环境变量

### 7.2 中期 (1-2 周)

1. **实现 Provider 健康检查**: 定期探测 Provider 可用性，动态调整 Fallback 链
2. **任务类型路由**: 按推理/代码/创意等分类，自动选择最合适的模型
3. **添加并发降级支持**: 同时尝试多个 Fallback 模型以减少延迟

### 7.3 长期 (1 月+)

1. **实现动态热加载**: 支持运行时添加/移除 Provider
2. **成本感知路由**: 根据 cost 字段优化每次调用的成本
3. **负载均衡**: 多 Provider 间智能分配请求
4. **缓存层**: 对重复的嵌入查询和通用响应进行缓存
5. **监控和告警**: 跟踪降级频率、失败率和响应时间

---

## 8. 架构图 (文本描述)

```
┌─────────────┐     ┌──────────────┐     ┌──────────────────┐
│  主会话     │────▶│  Model Router │────▶│  Fallback Chain  │
│  (Agent)    │     │  (Gateway)    │     │   (10 级降级)    │
└─────────────┘     └──────┬───────┘     └────────┬─────────┘
                           │                       │
                    ┌──────▼──────┐        ┌───────▼─────────┐
                    │  Provider   │        │  调度器(Scheduler)│
                    │  Manager    │        │  V2/V3/Daemon    │
                    └──────┬──────┘        └────────┬─────────┘
                           │                        │
         ┌─────────────────┼─────────────────┐      │
         ▼                 ▼                 ▼      │
    ┌────────┐      ┌──────────┐     ┌──────────┐   │
    │Moonshot│      │AliCoding │     │ Huoshan  │   │
    │  2 模型 │      │  9 模型  │     │ 10 模型  │   │
    └────────┘      └──────────┘     └──────────┘   │
                                                    │
         ┌──────────────────────────────────────────┘
         ▼
  ┌──────────────┐
  │   Tasks 表   │
  │  (Kanban DB) │
  └──────────────┘
```
