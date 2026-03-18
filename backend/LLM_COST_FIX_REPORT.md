# LLM 费用记录机制修复报告

**修复时间**: 2026-03-11  
**修复内容**: 确保每次 LLM 调用都记录费用到 token_usage 表

---

## ✅ 修复内容

### 1. 添加费用计算功能

**位置**: `app.py` (第 125-195 行)

**新增函数**:
- `calculate_cost(model_name, input_tokens, output_tokens)` - 根据模型和 token 数计算费用
- `record_token_usage(provider, model, prompt_tokens, completion_tokens, cost_usd)` - 记录 token 使用到数据库

**支持的模型价格** (USD per 1K tokens):
| 模型系列 | 代表模型 | 输入价格 | 输出价格 |
|---------|---------|---------|---------|
| Kimi/Moonshot | kimi-k2.5 | $0.002 | $0.008 |
| Qwen/阿里云 | qwen3.5-plus | $0.003 | $0.009 |
| DeepSeek | deepseek-chat | $0.00027 | $0.0011 |
| GLM/智谱 | glm-4 | $0.014 | $0.014 |
| GPT/OpenAI | gpt-4o | $0.005 | $0.015 |
| Claude/Anthropic | claude-3-5-sonnet | $0.003 | $0.015 |
| Gemini/Google | gemini-1.5-pro | $0.00125 | $0.005 |

### 2. 更新 ask_dudu API 记录费用

**位置**: `app.py` (第 2015-2025 行)

**修改内容**:
```python
# 在 LLM 调用成功后记录 token 使用
usage = result.get('usage', {})
prompt_tokens = usage.get('prompt_tokens', 0)
completion_tokens = usage.get('completion_tokens', 0)
if prompt_tokens > 0 or completion_tokens > 0:
    record_token_usage(
        provider='moonshot',
        model='kimi-k2.5',
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens
    )
```

### 3. 修复 Stats API

**位置**: `app.py` (第 2635-2645 行)

**修改前**: 从 `llm_configs` 表计算总费用（可能没有数据）  
**修改后**: 统一从 `token_usage` 表计算所有费用统计

```python
# 费用统计 (统一从 token_usage 表获取)
c.execute('SELECT SUM(cost_usd) FROM token_usage')
total_cost = c.fetchone()[0] or 0
```

### 4. 前端添加"暂无今日数据"提示

**位置**: `frontend/src/pages/LLMConfigs.tsx` (第 218-230 行)

**新增提示**:
```tsx
{(!stats?.today_cost || stats.today_cost === 0) && (
  <div style={{ 
    background: 'rgba(255,255,255,0.1)', 
    borderRadius: '8px', 
    padding: '12px',
    marginBottom: '16px',
    textAlign: 'center',
    fontSize: '0.9rem',
    opacity: 0.9
  }}>
    📊 暂无今日数据 - 开始使用 LLM 后会自动记录费用
  </div>
)}
```

---

## 🧪 测试结果

### 测试 1: 费用计算功能
```
✅ kimi-k2.5: 1000+500 tokens = $0.006000
✅ qwen3.5-plus: 2000+1000 tokens = $0.015000
✅ gpt-4o: 1500+800 tokens = $0.019500
✅ deepseek-chat: 5000+2000 tokens = $0.003550
```

### 测试 2: Token 使用记录
```
✅ 记录成功 - kimi-k2.5 - 1500 tokens - $0.006
```

### 测试 3: API 数据返回
```
✅ Stats API 正常
   - 今日费用：$0.0132
   - 本月费用：$0.0132
   - 累计费用：$1.2132

✅ Token Usage API 正常
   - 记录数：3
   - 最新记录：kimi-k2.5 - 1500 tokens - $0.006
```

**所有测试通过！** ✅

---

## 📊 数据库表结构

### token_usage 表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键 |
| timestamp | DATETIME | 记录时间 |
| provider | TEXT | 提供商 (如 'moonshot') |
| model | TEXT | 模型名称 (如 'kimi-k2.5') |
| prompt_tokens | INTEGER | 输入 token 数 |
| completion_tokens | INTEGER | 输出 token 数 |
| total_tokens | INTEGER | 总 token 数 |
| cost_usd | REAL | 费用 (USD) |

---

## 🔄 后续工作

### 需要添加费用记录的其他 LLM 调用点
目前只更新了 `ask_dudu` API，以下位置也需要添加：

1. **任务生成/脚本生成** - `task_worker.py` 中的 LLM 调用
2. **其他 AI 功能** - 所有调用 LLM API 的地方
3. **批量处理** - 如果有批量 LLM 调用，需要批量记录

### 建议
1. 创建统一的 LLM 调用封装函数，自动记录费用
2. 添加费用告警功能（如每日费用超过阈值时通知）
3. 添加费用趋势图表
4. 支持自定义模型价格配置

---

## 📝 相关文件

- **后端**: `~/.openclaw/workspace/kanban-react/backend/app.py`
- **前端**: `~/.openclaw/workspace/kanban-react/frontend/src/pages/LLMConfigs.tsx`
- **数据库**: `~/.openclaw/workspace/kanban-react/backend/kanban_v5.db`
- **测试脚本**: `test_llm_cost.py`

---

**修复完成！** 🎉
