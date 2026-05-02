-- =============================================================
-- SDS 系统性能优化 - 数据库索引添加脚本
-- 创建日期: 2026-04-23
-- =============================================================
-- 基于全面查询分析，优化的慢查询:
--   1. task_analyzer.py - 项目任务关联查询 (LEFT JOIN + GROUP BY)
--   2. subagent_scheduler.py - 待处理任务排序查询
--   3. monitoring_72h.py - 进行中任务状态查询
--   4. observability_dashboard.py - 状态分组统计
--   5. auto_task_generator.py - 模糊项目名称查询
--   6. task_analyzer.py - 时间范围停滞任务查询
--   7. safety_guardrails.py - 大规模全表扫描
-- =============================================================

-- =============================================================
-- 索引组1: tasks 表关键索引
-- tasks 表共 1401 行，频繁被按状态+优先级+时间查询
-- =============================================================

-- 1.1 状态 + 优先级复合索引（覆盖调度器查询）
-- 用于: sds/subagent_scheduler.py - 待处理任务优先级排序
-- 优化前: 全表扫描 → status IN ('pending','failed_retryable') + ORDER BY priority, id
-- 优化后: 索引覆盖过滤+排序
CREATE INDEX idx_tasks_status_priority_id 
ON tasks (status, priority, id);

-- 1.2 状态 + 更新时间复合索引（覆盖停滞任务分析）
-- 用于: sds/task_analyzer.py - 按小时计算停滞任务
-- 优化前: status条件+hours_since_update计算 → 全表扫描
-- 优化后: 索引前缀过滤+覆盖索引
CREATE INDEX idx_tasks_status_updated 
ON tasks (status, updated_at);

-- 1.3 项目ID索引（覆盖关联查询）
-- 用于: sds/task_analyzer.py - tasks LEFT JOIN projects
-- 优化前: project_id无索引，Nested Loop全扫描
-- 优化后: 索引关联
CREATE INDEX idx_tasks_project_id 
ON tasks (project_id);

-- 1.4 任务类型索引（覆盖仪表盘统计）
-- 用于: sds/observability_dashboard.py - 自动生成任务统计
-- 优化前: task_type无索引
CREATE INDEX idx_tasks_task_type 
ON tasks (task_type);

-- 1.5 创建日期索引（覆盖时间范围查询）
-- 用于: 按日期范围统计
CREATE INDEX idx_tasks_created_date 
ON tasks (created_date);

-- 1.6 更新时间单独索引（覆盖排序）
-- 用于: 多模块的 ORDER BY updated_at DESC
CREATE INDEX idx_tasks_updated_at 
ON tasks (updated_at);

-- =============================================================
-- 索引组2: projects 表关键索引
-- projects 表共 73 行，查询频率高
-- =============================================================

-- 2.1 项目状态索引
-- 用于: 活跃项目查询
-- 优化前: status无索引
CREATE INDEX idx_projects_status 
ON projects (status);

-- 2.2 项目名称全文索引
-- 用于: sds/auto_task_generator.py - LIKE '%name%' 模糊搜索
-- 优化前: LIKE %xxx% 无法使用前缀索引
-- 优化后: 虽然不可B-tree优化LIKE前导通配符，但覆盖查询可减少回表
CREATE INDEX idx_projects_name 
ON projects (name(100));

-- 2.3 项目主任务ID索引
-- 用于: 快速查找特定项目
CREATE INDEX idx_projects_main_task 
ON projects (main_task_id);

-- =============================================================
-- 索引组3: attachments 附件表索引
-- attachments 表共 652 行
-- =============================================================

-- 3.1 创建时间索引
-- 用于: 按时间排序附件列表
-- 优化前: created_at无索引
CREATE INDEX idx_attachments_created_at 
ON attachments (created_at);

-- 3.2 文件类型索引
-- 用于: 按类型过滤附件
CREATE INDEX idx_attachments_file_type 
ON attachments (file_type);

-- =============================================================
-- 索引组4: sub_tasks 子任务表索引
-- sub_tasks 表共 275 行
-- =============================================================

-- 4.1 项目ID索引
-- 用于: 按项目查询子任务
CREATE INDEX idx_sub_tasks_project_id 
ON sub_tasks (project_id);

-- 4.2 状态索引
-- 用于: 按状态过滤子任务
CREATE INDEX idx_sub_tasks_status 
ON sub_tasks (status(50));

-- 4.3 父任务ID索引
-- 用于: 按父任务查询子任务
CREATE INDEX idx_sub_tasks_parent 
ON sub_tasks (parent_task_id);

-- =============================================================
-- 索引组5: task_metrics 和 task_history 表
-- =============================================================

-- 5.1 任务度量表索引
-- 用于: 性能分析
CREATE INDEX idx_task_metrics_task_id 
ON task_metrics (task_id);

-- =============================================================
-- 索引添加完成
-- 总计添加: 14 个索引
-- =============================================================
