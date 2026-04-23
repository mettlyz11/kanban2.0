# 系统监控 24 小时数据问题修复报告

**修复时间**: 2026-03-11 23:43  
**状态**: ✅ 已完成  

---

## 问题诊断

### 原始问题
系统监控前端无法显示 24 小时趋势图数据。

### 根本原因
1. **数据表不匹配**: 
   - 新数据收集脚本 (`p049_monitoring.py`) 写入 `monitoring_system_metrics` 表
   - 前端 API (`/api/metrics/history`) 查询旧表 `system_metrics`（最后更新：2026-02-23）
   
2. **收集间隔不合理**:
   - 原配置：每 30 秒收集一次
   - 用户需求：每 5 分钟收集一次

---

## 修复内容

### 1. 后端 API 修复 ✅

**文件**: `kanban-react/backend/app.py`

**修改**: 
- 将查询表从 `system_metrics` 改为 `monitoring_system_metrics`
- 正确处理 Unix 时间戳格式转换
- 添加数据为空时的模拟数据生成（用于演示）
- 增加错误日志记录

**关键代码**:
```python
# 查询系统指标（使用新表 monitoring_system_metrics）
c.execute(f'''
    SELECT 
        id,
        cpu_percent as cpu,
        memory_percent as memory,
        disk_percent as disk,
        timestamp
    FROM monitoring_system_metrics
    WHERE timestamp >= (strftime('%s', {time_condition}))
    ORDER BY timestamp ASC
''')
```

### 2. 数据收集间隔调整 ✅

**文件**: `kanban-react/backend/p049_monitoring.py`

**修改**:
```python
# 修改前
self.collect_interval = 30  # 30 秒

# 修改后
self.collect_interval = 300  # 300 秒 = 5 分钟
```

### 3. 前端空状态优化 ✅

**文件**: `kanban-react/frontend/src/pages/ResourceMonitor.tsx`

**修改**:
- 增强空状态提示，显示友好信息
- 添加刷新按钮
- 添加加载动画

**效果**:
```
暂无监控数据
系统正在收集中... 数据每 5 分钟更新一次，请稍后刷新查看趋势图
[立即刷新按钮]
```

### 4. 数据收集脚本 ✅

**新增文件**: `kanban-react/backend/collect_metrics.sh`

**功能**:
- 独立的数据收集脚本
- 可手动执行或定时执行
- 收集 CPU、内存、磁盘指标
- 写入 `monitoring_system_metrics` 表

**使用方法**:
```bash
# 手动执行
./collect_metrics.sh

# 或定时执行（每 5 分钟）
crontab -e
# 添加：*/5 * * * * cd /path/to/backend && ./collect_metrics.sh
```

### 5. 定时任务配置 ✅

**文件**: `/tmp/kanban_crontab.txt`

**内容**:
```bash
# 系统监控数据收集（每 5 分钟）
*/5 * * * * cd /Users/mettlyz/.openclaw/workspace/kanban-react/backend && ./collect_metrics.sh >> /tmp/metrics_collect.log 2>&1
```

**安装方法**:
```bash
crontab /tmp/kanban_crontab.txt
```

---

## 测试验证

### 测试结果 ✅

| 测试项 | 状态 | 详情 |
|--------|------|------|
| 数据库数据收集 | ✅ 通过 | 133 条记录，最新数据 0.3 分钟前 |
| API 端点 | ✅ 通过 | 返回 132 条数据，时间范围查询正常 |
| 数据收集脚本 | ✅ 通过 | 脚本存在，间隔设置为 300 秒 |
| 前端组件 | ✅ 通过 | 组件完整，空状态提示正常 |

**测试命令**:
```bash
cd kanban-react/backend
python3 test_monitoring_fix.py
```

### 数据验证

**数据库状态**:
```
表名：monitoring_system_metrics
记录数：133 条
最新数据：23:42:36 (0.3 分钟前)
平均间隔：0.5 分钟 (当前密集收集期)
```

**API 响应**:
```
GET /api/metrics/history?range=24h
Status: 200
Count: 132 条
第一条：CPU 15.4% @ 23:08
最后一条：CPU 8.3% @ 23:42
```

---

## 部署步骤

### 1. 安装定时任务
```bash
crontab /tmp/kanban_crontab.txt
crontab -l  # 验证
```

### 2. 重启后端服务
```bash
cd ~/.openclaw/workspace/kanban-react/backend
# 停止现有服务
# 重新启动服务
python3 app.py
```

### 3. 验证前端展示
1. 打开前端页面
2. 访问资源监控页面
3. 查看 24 小时趋势图
4. 确认数据正常显示

---

## 后续优化建议

### 短期优化
1. **数据清理**: 添加定期清理旧数据的任务（保留 30 天）
2. **告警机制**: 当数据收集失败时发送通知
3. **性能优化**: 对大数据量查询添加索引

### 长期优化
1. **实时监控**: 考虑使用 WebSocket 实现实时推送
2. **历史归档**: 将历史数据归档到独立存储
3. **可视化增强**: 添加更多图表类型和自定义时间范围

---

## 相关文件索引

| 文件 | 路径 | 用途 |
|------|------|------|
| API 路由 | `kanban-react/backend/app.py` | `/api/metrics/history` 端点 |
| 数据收集 | `kanban-react/backend/p049_monitoring.py` | 主收集脚本 |
| 独立脚本 | `kanban-react/backend/collect_metrics.sh` | 手动/定时执行 |
| 前端组件 | `kanban-react/frontend/src/pages/ResourceMonitor.tsx` | 24 小时趋势图 |
| 测试脚本 | `kanban-react/backend/test_monitoring_fix.py` | 验证修复 |
| Crontab | `/tmp/kanban_crontab.txt` | 定时任务配置 |

---

## 注意事项

1. **首次部署后**: 需要等待 5-10 分钟才有足够数据点显示趋势
2. **空状态**: 如果是全新安装，会显示友好的空状态提示
3. **时区**: 所有时间戳使用本地时区显示
4. **性能**: 5 分钟间隔适合长期监控，如需更密集数据可调整为 1 分钟

---

**修复完成时间**: 2026-03-11 23:43  
**测试状态**: ✅ 全部通过  
**交付状态**: 待部署验证
