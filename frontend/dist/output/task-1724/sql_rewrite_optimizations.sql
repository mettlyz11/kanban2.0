-- =============================================================
-- SDS 系统 SQL 查询重写优化方案
-- 日期: 2026-04-23
-- =============================================================
-- 背景: 1401条tasks, 73条projects, 652条attachments
-- 核心问题: 表结构使用大量 TEXT 类型，索引选择受限
-- 优化策略: 重构查询 + 覆盖索引 + 减少回表
-- =============================================================

-- =============================================================
-- 优化1: 待处理任务按优先级排序
-- 原查询 (subagent_scheduler.py:66-75):
--   SELECT id, number, title, status, priority, project_id, ...
--   WHERE status IN ('pending', 'failed_retryable')
--   ORDER BY priority DESC, id ASC
--   LIMIT N
-- 问题: status和priority均为TEXT，无法创建长复合索引
-- =============================================================

-- 优化方案: 利用新增的 idx_tasks_status_priority_id 索引
-- MySQL可使用索引前缀(status(50), priority(20), id) 进行索引排序
-- 但TEXT前缀索引的排序能力有限，补充写法:
-- 改写为: 
SELECT 
  t.id, t.number, t.title, t.status, t.priority, 
  t.project_id, t.retry_count, t.updated_at
FROM tasks t FORCE INDEX (idx_tasks_status_priority_id)
WHERE t.status IN ('pending', 'failed_retryable')
ORDER BY t.priority DESC, t.id ASC
LIMIT 10;

-- =============================================================
-- 优化2: 项目-任务关联分析
-- 原查询 (task_analyzer.py:59-68):
--   SELECT p.id, p.name, p.status, COUNT(t.id) as task_count
--   FROM projects p LEFT JOIN tasks t ON p.id = t.project_id
--   WHERE p.status = 'active'
--   GROUP BY p.id, p.name, p.status
-- =============================================================

-- 优化方案: 先过滤活跃项目，减小驱动表
SELECT 
  p.id, p.name, p.status,
  (SELECT COUNT(*) FROM tasks t WHERE t.project_id = p.id) as task_count
FROM projects p
WHERE p.status = 'active'
ORDER BY p.id;

-- =============================================================
-- 优化3: 停滞任务检测
-- 原查询 (task_analyzer.py:94-102):
--   SELECT id, number, title, status, updated_at,
--          TIMESTAMPDIFF(HOUR, updated_at, NOW()) as hours_since_update
--   WHERE status IN ('pending', 'in_progress')
--   ORDER BY hours_since_update DESC
-- =============================================================

-- 优化方案: 用索引过滤(status, updated_at)，避免排序时计算函数
-- 直接在 WHERE 中过滤过时的任务
SELECT 
  id, number, title, status, updated_at,
  TIMESTAMPDIFF(HOUR, updated_at, NOW()) as hours_since_update
FROM tasks USE INDEX (idx_tasks_status_updated)
WHERE status IN ('pending', 'in_progress')
  AND updated_at < NOW()
ORDER BY updated_at ASC
LIMIT 20;

-- =============================================================
-- 优化4: 已完成任务汇总
-- 原查询 (subagent_scheduler.py:250-258):
--   SELECT id, number, title, status, ...
--   WHERE status = 'completed'
--   ORDER BY updated_at DESC
-- =============================================================

-- 优化方案: 使用新增索引 idx_tasks_status_updated
SELECT 
  id, number, title, status, task_summary,
  result_summary, updated_at
FROM tasks USE INDEX (idx_tasks_status_updated)
WHERE status = 'completed'
ORDER BY updated_at DESC
LIMIT 20;

-- =============================================================
-- 优化5: 按状态分组统计
-- 原查询 (observability_dashboard.py:58-62):
--   SELECT status, COUNT(*) as count FROM tasks GROUP BY status
-- =============================================================

-- 优化方案: 覆盖索引查询，使用 idx_tasks_status_priority_id
-- 只需扫描索引，无需回表
SELECT 
  COALESCE(status, 'unknown') as status,
  COUNT(*) as count
FROM tasks FORCE INDEX (idx_tasks_status_priority_id)
GROUP BY status
ORDER BY count DESC;

-- =============================================================
-- 优化6: 自动生成任务按日期统计
-- 原查询 (observability_dashboard.py:94-101):
--   SELECT DATE(created_date) as date, COUNT(*) as count
--   WHERE task_type = 'auto_generated'
--   GROUP BY DATE(created_date)
-- =============================================================

-- 优化方案: 使用 idx_tasks_task_type + idx_tasks_created_date
-- MySQL无法跨列索引，改用临时表或子查询
SELECT 
  DATE(t.created_date) as date,
  COUNT(*) as count
FROM tasks t USE INDEX (idx_tasks_created_date)
WHERE t.task_type = 'auto_generated'
  AND t.created_date IS NOT NULL
GROUP BY DATE(t.created_date)
ORDER BY date DESC
LIMIT 30;

-- =============================================================
-- 优化7: 项目模糊搜索 (LIKE前导通配符)
-- 原查询 (auto_task_generator.py:134-135):
--   SELECT id FROM projects WHERE name LIKE %s LIMIT 1
-- =============================================================

-- LIKE '%keyword%' 无法使用B-tree索引
-- 优化方案: 全表扫描(73条记录，表扫描比索引快)
-- 无需优化，使用 LIMIT 1 限制即可
SELECT id, name, status 
FROM projects 
WHERE name LIKE '%SDS%'
LIMIT 10;

-- =============================================================
-- 优化8: 全表扫描限制 (safety_guardrails.py:272-273)
-- 原查询: SELECT * FROM tasks ORDER BY id DESC LIMIT 1000
-- =============================================================

-- 优化方案: 指定需要的列，加上索引提示
SELECT 
  id, number, title, task_type, status, created_date
FROM tasks FORCE INDEX (PRIMARY)
ORDER BY id DESC
LIMIT 1000;

-- =============================================================
-- 优化9: 子任务关联分组
-- 原查询: LEFT JOIN sub_tasks + projects GROUP BY
-- =============================================================

-- 优化方案: 使用新增索引
SELECT 
  s.project_id, 
  (SELECT p.name FROM projects p WHERE p.id = s.project_id) as project_name,
  s.status,
  COUNT(*) as sub_count
FROM sub_tasks s USE INDEX (idx_sub_tasks_project_id)
GROUP BY s.project_id, s.status;

-- =============================================================
-- 优化10: 系统健康检查 (monitoring_72h.py)
-- 原查询: 多个独立COUNT查询
-- =============================================================

-- 优化方案: 合并为一条查询，减少数据库往返
SELECT 
  COUNT(*) as total_tasks,
  SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending_count,
  SUM(CASE WHEN status = 'in_progress' THEN 1 ELSE 0 END) as in_progress_count,
  SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_count,
  SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) as cancelled_count,
  SUM(CASE WHEN status = 'archived' THEN 1 ELSE 0 END) as archived_count,
  SUM(CASE WHEN status IN ('pending', 'in_progress') 
            AND updated_at < DATE_SUB(NOW(), INTERVAL 24 HOUR) 
       THEN 1 ELSE 0 END) as stale_count
FROM tasks;

-- =============================================================
-- 优化完成
-- =============================================================
