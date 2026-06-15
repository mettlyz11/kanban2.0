-- ======================================
-- SDS系统72小时运行报告 - 数据库优化脚本
-- 生成时间: 2026-04-24
-- 版本: v1.0
-- ======================================

-- ======================================
-- 1. 索引优化
-- ======================================

-- tasks表复合索引：提高按时间和状态查询性能
CREATE INDEX IF NOT EXISTS idx_tasks_created_status 
ON tasks(created_at, status);

-- tasks表类型索引：提高按类型统计性能
CREATE INDEX IF NOT EXISTS idx_tasks_type 
ON tasks(type);

-- subagent_runs表时间和状态索引
CREATE INDEX IF NOT EXISTS idx_subagent_runs_created_status 
ON subagent_runs(created_at, status);

-- health_checks表时间索引
CREATE INDEX IF NOT EXISTS idx_health_checks_time 
ON health_checks(check_time);

-- ======================================
-- 2. 查询性能分析
-- ======================================

-- 查看慢查询配置
SHOW VARIABLES LIKE 'long_query_time';

-- 查看当前慢查询日志状态
SHOW VARIABLES LIKE 'slow_query_log';

-- 建议：将long_query_time设置为1秒，捕获所有慢查询
-- SET GLOBAL long_query_time = 1;

-- ======================================
-- 3. 表结构优化建议
-- ======================================

-- 为tasks表添加执行时间统计字段（便于后续性能分析）
ALTER TABLE tasks 
ADD COLUMN IF NOT EXISTS execution_seconds INT DEFAULT 0 
COMMENT '任务执行秒数';

ALTER TABLE tasks 
ADD COLUMN IF NOT EXISTS wait_seconds INT DEFAULT 0 
COMMENT '任务等待秒数';

-- 为subagent_runs表添加资源使用统计
ALTER TABLE subagent_runs 
ADD COLUMN IF NOT EXISTS cpu_usage FLOAT DEFAULT 0 
COMMENT 'CPU使用率峰值';

ALTER TABLE subagent_runs 
ADD COLUMN IF NOT EXISTS memory_usage_mb INT DEFAULT 0 
COMMENT '内存使用峰值(MB)';

-- ======================================
-- 4. 分区表建议（数据量超过100万行时实施）
-- ======================================

-- 按月分区tasks表示例（未来扩展）
-- ALTER TABLE tasks PARTITION BY RANGE (TO_DAYS(created_at)) (
--     PARTITION p202604 VALUES LESS THAN (TO_DAYS('2026-05-01')),
--     PARTITION p202605 VALUES LESS THAN (TO_DAYS('2026-06-01'))
-- );

-- ======================================
-- 5. 数据库连接池配置建议
-- ======================================

-- 当前最大连接数：120
-- 建议值：根据业务增长调整为 200-300
-- SET GLOBAL max_connections = 200;

-- 查看当前连接数
SHOW STATUS LIKE 'Threads_connected';

-- ======================================
-- 6. 执行验证
-- ======================================

-- 验证索引创建成功
SELECT 
    TABLE_NAME, 
    INDEX_NAME, 
    COLUMN_NAME,
    SEQ_IN_INDEX
FROM INFORMATION_SCHEMA.STATISTICS 
WHERE TABLE_SCHEMA = DATABASE()
AND TABLE_NAME IN ('tasks', 'subagent_runs', 'health_checks')
ORDER BY TABLE_NAME, INDEX_NAME, SEQ_IN_INDEX;

-- 查看表大小统计
SELECT 
    TABLE_NAME,
    ROUND(((DATA_LENGTH + INDEX_LENGTH) / 1024 / 1024), 2) AS '大小(MB)',
    TABLE_ROWS AS '行数'
FROM INFORMATION_SCHEMA.TABLES
WHERE TABLE_SCHEMA = DATABASE()
AND TABLE_NAME IN ('tasks', 'subagent_runs', 'health_checks');

-- ======================================
-- 优化完成
-- ======================================
-- SELECT '数据库优化脚本执行完成' AS status;
