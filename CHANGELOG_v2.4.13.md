# 看板系统 v2.4.13 - 纯 MySQL 化

**发布日期**: 2026-03-18  
**类型**: 重大更新 - 移除 SQLite 支持

## 🎯 更新目标
- 完全移除 SQLite 引用
- 纯 MySQL/RDS 化
- 提升系统稳定性和性能

## 📝 变更内容

### 核心文件修改

1. **task_worker.py**
   - ✅ 移除 sqlite3 导入，改用 pymysql
   - ✅ 重写数据库连接逻辑使用 MySQL/RDS
   - ✅ 移除本地 SQLite 数据库路径依赖

2. **db_config.py**
   - ✅ 完全移除 SQLite 配置
   - ✅ 纯 MySQL/RDS 配置
   - ✅ 简化连接管理

3. **app.py**
   - ✅ 移除 DB_TYPE 切换逻辑
   - ✅ 固定为 MySQL 模式
   - ✅ 移除 SQLite 相关注释

4. **.env**
   - ✅ 移除 SQLite 配置项
   - ✅ 简化为纯 MySQL 配置

5. **迁移脚本**
   - ✅ migrate_task_worker.py - 标记为已弃用
   - ✅ migrate_key_tables.py - 标记为已弃用

### 数据库变更

**tasks 表新增字段**:
- `slurm_job_id` (INTEGER) - SLURM 作业 ID
- `slurm_output_file` (TEXT) - SLURM 输出文件路径
- `retry_count` (INTEGER, DEFAULT 0) - 重试次数

## 🔧 技术细节

### MySQL 连接配置
```python
MYSQL_CONFIG = {
    'host': 'rm-2zew4su9p966e8x2ofo.mysql.rds.aliyuncs.com',
    'port': 3306,
    'user': 'kanban',
    'database': 'kanban',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor,
}
```

### 向后兼容性
- ❌ 不再支持 SQLite
- ✅ 完全兼容 MySQL 8.0+
- ✅ 兼容阿里云 RDS MySQL

## ✅ 验证清单

- [x] 核心文件无 sqlite3 导入
- [x] 数据库连接测试通过
- [x] tasks 表字段迁移完成
- [x] task_worker.py 语法检查通过
- [x] 备份文件已创建

## 📦 备份位置

- **本地备份**: `/opt/kanban-react/backend/*.backup`
- **Git 备份**: github.com/mettlyz11/kanban-system
- **服务器备份**: `/opt/kanban-react/backups/`

## 🚀 部署说明

1. 备份现有文件（自动执行）
2. 上传新版本文件
3. 执行数据库迁移（添加新字段）
4. 重启后端服务
5. 验证功能正常

## ⚠️ 注意事项

- 此版本不再支持 SQLite
- 如需回滚，请使用备份文件
- 确保 RDS MySQL 可访问

---
**版本**: v2.4.13  
**作者**: OpenClaw Subagent  
**审核**: 待用户验收
