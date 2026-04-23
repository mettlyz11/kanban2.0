# 任务审核系统 - 使用说明

## 概述

任务审核系统确保所有自动生成的任务（齿轮系统、战略协调员、感知Agent等）都必须经过人工审核后才能执行。

## 核心文件

### 新增文件

| 文件 | 说明 |
|------|------|
| `task_audit_system.py` | 任务审核系统核心 |
| `gear_system_enhanced.py` | 增强型齿轮系统 |
| `supervisor_system_enhanced.py` | 增强型监督系统 |
| `long_thinking_enhanced.py` | 增强型长思考系统 |
| `perception_agent_enhanced.py` | 增强型感知Agent |
| `audit_routes.py` | 审核API路由 |
| `upgrade_db_audit.py` | 数据库升级脚本 |
| `install_audit_system.py` | 安装配置脚本 |

## 快速开始

### 1. 安装

```bash
cd kanban-react/backend
python3 install_audit_system.py
```

### 2. 修改app.py

在 `app.py` 中添加审核路由：

```python
from audit_routes import register_audit_routes

# ... 其他代码 ...

register_audit_routes(app)
```

### 3. 重启服务

```bash
# 如果使用supervisor
sudo supervisorctl restart kanban-react

# 或手动重启
python3 app.py
```

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                     任务生成源                               │
├──────────────┬──────────────┬──────────────┬────────────────┤
│  齿轮系统     │ 战略协调员    │  长思考系统   │   感知Agent    │
└──────┬───────┴──────┬───────┴──────┬───────┴────────┬───────┘
       │              │              │                │
       └──────────────┴──────┬───────┴────────────────┘
                             │
                    ┌────────▼─────────┐
                    │  TaskAuditSystem  │
                    │   任务审核系统    │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │ manual_review_   │
                    │    tasks 表      │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │    人工审核      │
                    └────────┬─────────┘
                             │
              ┌──────────────┼──────────────┐
              │              │              │
        ┌─────▼─────┐  ┌────▼─────┐  ┌────▼─────┐
        │  批准     │  │  拒绝    │  │  待审核  │
        └─────┬─────┘  └────┬─────┘  └────┬─────┘
              │             │             │
        ┌─────▼─────┐  ┌────▼─────┐  ┌────▼─────┐
        │ 可执行    │  │  取消    │  │  阻塞    │
        └───────────┘  └──────────┘  └──────────┘
```

## API接口

### 审核任务管理

```http
# 获取待审核任务
GET /api/audit/tasks/pending
GET /api/audit/tasks/pending?source=gear_system

# 批准任务
POST /api/audit/tasks/{audit_id}/approve
{
    "reviewer": "admin",
    "notes": "审核通过，可以执行"
}

# 拒绝任务
POST /api/audit/tasks/{audit_id}/reject
{
    "reviewer": "admin",
    "reason": "资源不足，暂缓执行"
}

# 获取审核统计
GET /api/audit/tasks/stats
```

### 执行前检查

```http
# 检查任务是否可以执行
GET /api/audit/tasks/{task_id}/check

# 响应示例
{
    "success": true,
    "task_id": 123,
    "can_execute": false,
    "status": "pending",
    "message": "任务待审核，请先审核后再执行"
}
```

### 监督系统

```http
# 强制执行审核策略
POST /api/audit/supervisor/enforce
{
    "task_id": 123
}

# 扫描未审核任务
POST /api/audit/supervisor/scan

# 获取监督报告
GET /api/audit/supervisor/report

# 获取监督统计
GET /api/audit/supervisor/stats

# 发送待审核提醒
POST /api/audit/supervisor/notify
```

### 仪表板

```http
# 获取审核仪表板
GET /api/audit/dashboard
```

## 数据库结构

### tasks 表新增字段

```sql
ALTER TABLE tasks ADD COLUMN requires_audit INTEGER DEFAULT 1;
ALTER TABLE tasks ADD COLUMN audit_status TEXT DEFAULT 'pending';
```

### manual_review_tasks 表

```sql
CREATE TABLE manual_review_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_type TEXT,           -- 任务类型 (gear_system, strategy_coordinator, etc.)
    title TEXT NOT NULL,
    description TEXT,
    source TEXT,              -- 来源系统
    source_id INTEGER,        -- 关联的任务ID
    status TEXT DEFAULT 'pending',  -- pending/approved/rejected
    priority TEXT DEFAULT 'medium',
    notes TEXT,               -- 审核备注
    reviewer TEXT,            -- 审核人
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);
```

## 使用示例

### 1. 注册齿轮任务

```python
from task_audit_system import register_gear_task

result = register_gear_task(
    title="修复系统错误",
    description="检测到API错误，需要修复",
    priority="high"
)

print(result)
# {
#     "success": True,
#     "task_id": 123,
#     "audit_id": 456,
#     "task_number": "AUD001",
#     "status": "pending_audit",
#     "message": "任务已创建并提交审核"
# }
```

### 2. 执行前检查

```python
from task_audit_system import check_task_before_execution

result = check_task_before_execution(task_id=123)

if result['can_execute']:
    # 执行任务
    execute_task(123)
else:
    print(f"无法执行: {result['message']}")
```

### 3. 批准任务

```python
from task_audit_system import approve_task

result = approve_task(
    audit_id=456,
    reviewer="admin",
    notes="审核通过"
)
```

## 审核状态流程

```
任务创建
    │
    ▼
┌───────────────┐
│ audit_status  │
│  = 'pending'  │
└───────┬───────┘
        │
   ┌────┴────┐
   │         │
   ▼         ▼
┌──────┐  ┌──────┐
│批准   │  │拒绝  │
│approved│  │rejected│
└───┬───┘  └──┬───┘
    │         │
    ▼         ▼
┌──────┐  ┌──────┐
│可执行 │  │已取消 │
└──────┘  └──────┘
```

## 配置选项

### 监督系统配置

在 `supervisor_system_enhanced.py` 中：

```python
# 自动创建审核请求
supervisor.auto_create_audit_requests()

# 定期检查
supervisor.scan_unaudited_tasks()
```

### 长思考系统配置

在 `long_thinking_enhanced.py` 中：

```python
# 所有生成的任务自动需要审核
engine = EnhancedLongThinkingEngine()
report = engine.run_analysis()  # 生成的任务全部待审核
```

## 故障排除

### 问题1: 任务无法执行

**原因**: 任务未审核

**解决**: 
```bash
# 查看待审核任务
curl /api/audit/tasks/pending

# 批准任务
curl -X POST /api/audit/tasks/{audit_id}/approve \
  -d '{"reviewer": "admin"}'
```

### 问题2: 数据库字段缺失

**原因**: 数据库未升级

**解决**:
```bash
python3 upgrade_db_audit.py
```

### 问题3: API返回404

**原因**: 路由未注册

**解决**: 在 `app.py` 中添加:
```python
from audit_routes import register_audit_routes
register_audit_routes(app)
```

## 监控和报告

### 查看审核统计

```bash
python3 -c "
from task_audit_system import task_audit_system
import json
stats = task_audit_system.get_stats()
print(json.dumps(stats, indent=2, ensure_ascii=False))
"
```

### 生成监督报告

```bash
python3 -c "
from supervisor_system_enhanced import supervisor
report = supervisor.generate_audit_report()
print(f'待审核: {report.pending_audit}')
print(f'已批准: {report.approved}')
print(f'已拒绝: {report.rejected}')
"
```

## 安全注意事项

1. **审核权限**: 确保只有授权用户可以批准/拒绝任务
2. **审计日志**: 所有审核操作都会被记录
3. **防重复**: 系统会自动防止重复创建审核任务
4. **超时处理**: 长时间未审核的任务会发送提醒

## 联系方式

如有问题，请联系系统管理员。

---

**文档版本**: 1.0  
**最后更新**: 2026-03-09
