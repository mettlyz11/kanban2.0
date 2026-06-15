# 自动化工作流程文档

## 流程概述

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  槽位空闲  │ ──→ │ 读取看板任务 │ ──→ │ Superpowers │
└─────────────┘     └─────────────┘     │   执行    │
                                              └──────┬──────┘
                                                     │
┌─────────────┐     ┌─────────────┐     ┌────────┴────────┐
│  产生新任务  │ ←── │  更新看板   │ ←── │  任务完成      │
│  (指导性)    │     │  (状态更新)  │     │ (自动检测)      │
└─────────────┘     └─────────────┘     └─────────────────┘
```

## 任务类型定义

### 1. 普通任务 (`type: normal`)
- **会被自动读取执行**
- 状态: `todo` → `in_progress` → `completed`
- 优先级: urgent/high/medium/low
- 使用Superpowers流程执行

### 2. 指导性任务 (`type: guide`)
- **只记录，不被读取执行**
- 用于工作流程、最佳实践、参考文档
- 状态保持 `guide`
- 作为知识库存在

## 自动化规则

### 槽位空闲时
```sql
SELECT * FROM tasks 
WHERE type = 'normal' 
  AND status IN ('todo', 'in_progress')
ORDER BY priority DESC, id DESC
LIMIT 5
```

### 任务完成后
```sql
UPDATE tasks 
SET status = 'completed', 
    updated_at = NOW(),
    result_summary = '...'
WHERE id = ?
```

### 从源产生新任务
- 七大人生目标 (T1-T7)
- 文献计量方法进展
- 系统健康检查
- 知识库维护

## 当前运行中的任务

| 任务 | 类型 | 状态 |
|------|------|------|
| T109平台发布 | normal | in_progress |
| ACS论文下载 | normal | in_progress |
| Browser-Use清理 | normal | completed |
| 揭牌仪式确认 | normal | completed |
| 财务资产评估 | normal | completed |

## 指导性任务示例

| 任务 | 类型 | 用途 |
|------|------|------|
| 本工作流程文档 | guide | 参考 |
| Browser-Use最佳实践 | guide | 参考 |
| 系统架构说明 | guide | 参考 |

## 文件位置

- 本文档: `/docs/workflow-automation.md`
- 最佳实践: `/docs/browser-use-best-practices.md`
- 任务报告: `/logs/task-*.md`

---

**最后更新**: 2026-04-11
**版本**: v1.0
