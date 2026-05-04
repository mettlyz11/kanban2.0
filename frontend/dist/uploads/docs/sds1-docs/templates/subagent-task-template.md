# 子代理任务模板（防重复执行版）

**版本**: v1.0 (2026-04-14)  
**用途**: 所有子代理启动时必须使用此模板

---

## 标准模板

```markdown
【看板任务 #{task_id} - {task_name}】

## 任务目标
{清晰描述任务目标和预期成果}

## 执行步骤
1. {步骤 1}
2. {步骤 2}
3. {步骤 3}

## 输出要求
- 生成文件：{文件路径}
- 更新记忆：{记忆文件路径}
- 看板更新：status, task_summary, execution_log

---

## 【任务完成强制动作】⭐⭐⭐⭐⭐

**完成后必须立即执行以下 SQL 更新（否则视为未完成）**：

```sql
UPDATE tasks SET 
  status = 'completed',
  task_summary = '{50-100 字核心成果摘要}',
  execution_log = '{执行日志摘要}',
  updated_at = NOW()
WHERE id = {task_id};
```

**示例**：
```sql
UPDATE tasks SET 
  status = 'completed',
  task_summary = 'Cycle 84 完成！Obsidian Vault 链接健康度 94.2%→97.74%。创建 869 个概念页，修复 2,483 条断链，剩余 4,034 条（去重冲突 + 历史路径问题）。',
  execution_log = '扫描 73,174 个.md 文件，178,648 个 wikilink，断链 4,034 次。生成报告：logs/cycle-84-96percent-final-report.md',
  updated_at = NOW()
WHERE id = 515;
```

**⚠️ 重要**：
- 必须在子代理代码中执行此 SQL
- `task_summary` 必须 50-100 字，包含关键数据/结论
- 主代理将在 completion 事件后验证数据库状态
- 未执行此 SQL 的任务视为未完成，可能导致重复执行

---

## 配置要求

| 配置项 | 值 | 说明 |
|--------|-----|------|
| **thinking** | `high` | 强制深度思考 |
| **runTimeoutSeconds** | `50400` | 14 小时超时 |
| **model** | 主代理指定 | 继承或指定模型 |

**启动示例**：
```python
sessions_spawn(
    label=f"task-{task_id}-{short_name}",
    task=task_description,  # 使用本模板
    thinking="high",
    runTimeoutSeconds=50400
)
```

---

## 防重复执行检查清单

**启动前**（主代理执行）：
- [ ] 检查 `task_summary IS NULL OR task_summary = ''`
- [ ] 检查相同任务名/Cycle 号是否有完成记录
- [ ] 确认任务状态与执行历史一致

**完成后**（子代理 + 主代理双重验证）：
- [ ] 子代理执行 SQL 更新 `status='completed'`
- [ ] 主代理验证数据库状态
- [ ] 确认 `task_summary` 已写入（50-100 字）

---

## 违规处理

| 违规次数 | 处理方式 |
|---------|---------|
| 第 1 次 | 记录到 MEMORY.md，立即修复数据库，暂停工作流 5 分钟 |
| 第 2 次 | 暂停工作流 30 分钟，强制学习防重复规则 |
| 第 3 次 | 请求用户介入，重置工作流权限 |
