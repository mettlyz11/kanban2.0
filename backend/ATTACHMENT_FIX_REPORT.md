# 看板系统附件修复报告

## 执行时间
2026-05-01 13:16-13:30 (Asia/Shanghai)

## 执行前状态

- 总附件记录: 5,173
- 孤儿附件（关联任务不存在）: 1,743
- 大小为0的附件: 5
- 有效附件: 3,421

## 调查发现

### 1. 文件存储位置
- 上传目录: /opt/kanban-react/frontend/public/uploads/docs/（前端可访问）
- 后端dist目录: /opt/kanban-react/backend/dist/uploads/docs/（构建产物）
- 后端uploads目录: /opt/kanban-react/backend/uploads/（几乎为空）

### 2. 文件分布情况
- 前端uploads目录: ~673个文件（最新到2026-04-30）
- 后端dist/uploads目录: ~592个文件（最新到2026-04-30）
- 大量附件URL指向 /uploads/docs/ 但文件不存在于任何目录

### 3. 文件缺失原因分析
- 数据库中有3,324条 /uploads/docs/ 路径的记录
- 但前端和dist目录总共只有约600-700个实际文件
- 约2,600+个附件文件物理缺失（可能是历史数据迁移或清理导致）

### 4. 路径问题
- 发现20条记录使用本地Mac路径 /Users/mettlyz/.openclaw/workspace/...
- 已修复为相对路径

## 修复操作

### 1. 备份
- 创建SQL备份: /opt/kanban-react/backend/backups/attachments_backup_20260501_131618.sql (780KB)
- 创建表备份: attachments_backup_20260501 (5,173条记录)

### 2. 清理无效记录
- 删除大小为0的附件: 5条记录已删除
- 删除孤儿附件: 1,738条记录已删除（关联任务不存在）

### 3. 修复路径
- 修复本地路径: 20条记录的Mac本地路径已修正为服务器相对路径

## 修复后状态

- 总附件记录: 3,430
- 孤儿附件: 0
- 大小为0的附件: 0
- 有效任务附件: 3,422
- 公司/人物附件: 8

## 仍然存在的问题

### 1. 物理文件大量缺失
- 约2,600+个附件记录对应的物理文件不存在
- 这些记录虽然关联有效任务，但文件已丢失
- 建议: 定期清理或标记这些无效记录

### 2. 文件存储分散
- 文件分布在多个目录: frontend/public/uploads/、backend/dist/uploads/、backend/attachments/
- 建议: 统一文件存储路径

### 3. 上传API配置
- 上传API配置路径: /opt/kanban-react/frontend/public/uploads/docs
- 但前端服务可能通过nginx或其他方式提供静态文件

## 建议后续操作

1. 定期清理: 建立定期检查和清理孤儿附件的机制
2. 文件备份: 对重要附件进行定期备份
3. 存储统一: 考虑统一文件存储位置，避免分散
4. 上传验证: 增强上传后的文件存在性验证
