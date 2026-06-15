# 看板任务类型定义

## 任务类型

### 1. normal (普通任务)
- **会被自动读取执行**
- 查询条件: `status IN ('todo', 'in_progress')`
- 使用Superpowers流程执行
- 完成后自动更新状态

### 2. guide (指导性任务)
- **只记录，不被读取执行**
- 用于工作流程、最佳实践、参考文档
- 状态保持 `guide`
- 作为知识库存在

## 自动化查询SQL

```sql
-- 自动执行查询 (只读取normal类型)
SELECT * FROM kanban.tasks 
WHERE task_type = 'normal' 
  AND status IN ('todo', 'in_progress')
ORDER BY FIELD(priority, 'urgent', 'high', 'medium', 'low'), 
         id DESC 
LIMIT 5;

-- 指导性任务查询 (不会被自动执行)
SELECT * FROM kanban.tasks 
WHERE task_type = 'guide';
```

## 当前任务分类

### normal 类型 (可执行)
- T109平台正式发布
- ACS论文批量下载
- Browser-Use残留进程清理
- 揭牌仪式准备
- 财务资产评估

### guide 类型 (指导性)
- 自动化工作流程文档
- Browser-Use最佳实践
- 系统架构说明

## 文件位置

- 本文档: `/docs/kanban-task-types.md`
- 流程文档: `/docs/workflow-automation.md`
- 最佳实践: `/docs/browser-use-best-practices.md`
