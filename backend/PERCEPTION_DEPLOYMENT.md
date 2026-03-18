# 感知 Agent 系统 - 部署文档

**版本**: 1.0.0  
**创建时间**: 2026-03-11  
**状态**: ✅ 已完成部署

---

## 📋 目录

1. [概述](#概述)
2. [已完成的工作](#已完成的工作)
3. [系统架构](#系统架构)
4. [安装与配置](#安装与配置)
5. [使用方法](#使用方法)
6. [API 文档](#api 文档)
7. [故障排查](#故障排查)
8. [文件清单](#文件清单)

---

## 概述

感知 Agent (Perception Agent) 是一个智能监控系统，用于：

- 📊 **日志监控**: 实时监控系统日志，识别错误和异常
- 🔍 **错误检测**: 自动检测和分类系统错误
- 📈 **指标监控**: 监控 CPU、内存、磁盘等资源使用情况
- 👤 **用户行为分析**: 记录和分析用户操作模式
- 🌐 **外部数据源**: 集成 GitHub、ArXiv、RSS 等外部信息源
- 💾 **事件存储**: 所有事件记录到 SQLite 数据库

---

## 已完成的工作

### ✅ 1. 数据库表创建
- 创建了 `perception_events` 表
- 添加了 4 个索引以优化查询性能
- 支持事件类型、严重级别、时间戳、哈希去重

### ✅ 2. API 路由集成
- 创建了 `perception_routes.py` 蓝图
- 集成了 7 个 API 端点
- 在 `app.py` 中自动启动感知 Agent

### ✅ 3. 启动脚本
- 创建了 `start_perception_agent.sh` 启动脚本
- 支持 start/stop/restart/status/logs 命令
- 自动检查依赖和配置

### ✅ 4. systemd 服务
- 创建了 `perception-agent.service` 服务文件
- 创建了 `install_systemd_service.sh` 安装脚本
- 支持开机自启和自动重启

### ✅ 5. 测试验证
- 创建了 `test_perception_agent.py` 测试脚本
- 所有 6 项测试通过
- 验证了数据库读写功能

### ✅ 6. 配置文件
- 完整的 `perception_config.yml` 配置
- 支持 5 种监听器
- 可自定义事件处理策略

---

## 系统架构

```
┌─────────────────────────────────────────────────┐
│           感知 Agent 系统                        │
├─────────────────────────────────────────────────┤
│                                                 │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────┐ │
│  │ 日志监听器  │  │ 错误监听器  │  │ 指标监听│ │
│  │ LogListener │  │ErrorListener│  │Metric   │ │
│  └──────┬──────┘  └──────┬──────┘  └────┬────┘ │
│         │                │               │      │
│         └────────────────┼───────────────┘      │
│                          │                      │
│                 ┌────────▼────────┐             │
│                 │  事件处理器     │             │
│                 │ EventProcessor  │             │
│                 └────────┬────────┘             │
│                          │                      │
│         ┌────────────────┼───────────────┐      │
│         │                │               │      │
│  ┌──────▼──────┐  ┌──────▼──────┐  ┌────▼────┐ │
│  │ 行为监听器  │  │  外部监听器  │  │ 数据库  │ │
│  │Behavior     │  │External     │  │ SQLite  │ │
│  │Listener     │  │Listener     │  │         │ │
│  └─────────────┘  └─────────────┘  └─────────┘ │
│                                                 │
└─────────────────────────────────────────────────┘
```

---

## 安装与配置

### 前置要求

- Python 3.8+
- SQLite3
- Flask
- PyYAML

### 快速安装

```bash
# 进入目录
cd ~/.openclaw/workspace/kanban-react/backend

# 运行检查
./start_perception_agent.sh check

# 启动 Agent
./start_perception_agent.sh start

# 查看状态
./start_perception_agent.sh status
```

### 安装 systemd 服务（Linux）

```bash
# 安装服务（需要 root 权限）
sudo ./install_systemd_service.sh

# 验证服务
systemctl status perception-agent

# 查看日志
journalctl -u perception-agent -f
```

### 配置文件

编辑 `perception_config.yml` 自定义行为：

```yaml
listeners:
  log_watcher:
    enabled: true
    poll_interval: 2  # 秒
    files:
      - "~/.openclaw/workspace/kanban-react/server.log"
  
  error_watcher:
    enabled: true
    dedup_window: 3600  # 秒
  
  metric_watcher:
    enabled: true
    poll_interval: 30
  
  behavior_watcher:
    enabled: true
  
  external_watcher:
    enabled: false  # 默认关闭
```

---

## 使用方法

### 命令行操作

```bash
# 启动
./start_perception_agent.sh start

# 停止
./start_perception_agent.sh stop

# 重启
./start_perception_agent.sh restart

# 查看状态
./start_perception_agent.sh status

# 查看实时日志
./start_perception_agent.sh logs

# 运行检查
./start_perception_agent.sh check

# 运行测试
python3 test_perception_agent.py
```

### systemd 服务操作

```bash
# 启动服务
sudo systemctl start perception-agent

# 停止服务
sudo systemctl stop perception-agent

# 重启服务
sudo systemctl restart perception-agent

# 查看状态
sudo systemctl status perception-agent

# 开机自启
sudo systemctl enable perception-agent

# 禁用开机自启
sudo systemctl disable perception-agent

# 查看日志
sudo journalctl -u perception-agent -f
```

---

## API 文档

### 基础 URL

```
http://localhost:5001/api/perception
```

### 端点列表

#### 1. GET /status
获取感知 Agent 运行状态

**响应示例**:
```json
{
  "success": true,
  "data": {
    "running": true,
    "listeners": 4,
    "events_processed": 123
  }
}
```

#### 2. GET /events
获取事件日志

**参数**:
- `limit`: 返回数量 (默认 100)
- `offset`: 偏移量 (默认 0)
- `severity`: 按级别过滤 (info/warning/error/critical)
- `type`: 按类型过滤

**响应示例**:
```json
{
  "success": true,
  "data": {
    "events": [
      {
        "id": 1,
        "event_type": "system_startup",
        "severity": "info",
        "source": "backend",
        "message": "看板系统后端服务启动",
        "timestamp": "2026-03-11T23:22:10"
      }
    ],
    "total": 150,
    "limit": 100,
    "offset": 0
  }
}
```

#### 3. POST /test
发送测试事件

**请求体**:
```json
{
  "type": "test",
  "severity": "low",
  "message": "测试消息",
  "metadata": {"key": "value"}
}
```

#### 4. GET /config
获取配置文件

#### 5. POST /record-action
记录用户行为

**请求体**:
```json
{
  "user_id": "user_123",
  "action": "create_task",
  "target": "task_456",
  "metadata": {"project": "proj_789"}
}
```

#### 6. POST /start
启动感知 Agent

#### 7. POST /stop
停止感知 Agent

---

## 故障排查

### 问题 1: Agent 无法启动

**症状**: 启动脚本报错

**解决方案**:
```bash
# 检查依赖
./start_perception_agent.sh check

# 查看日志
cat perception_agent.log

# 手动启动调试
python3 perception_agent.py
```

### 问题 2: 数据库表不存在

**症状**: 报错 "no such table: perception_events"

**解决方案**:
```bash
python3 init_perception_db.py
```

### 问题 3: systemd 服务启动失败

**症状**: `systemctl status perception-agent` 显示失败

**解决方案**:
```bash
# 查看详细错误
sudo journalctl -u perception-agent -n 50

# 重新安装服务
sudo ./install_systemd_service.sh

# 检查权限
ls -la start_perception_agent.sh
chmod +x start_perception_agent.sh
```

### 问题 4: API 返回 404

**症状**: 访问 `/api/perception/...` 返回 404

**解决方案**:
1. 确认 app.py 中已导入 perception_routes
2. 重启 Flask 应用
3. 检查路由前缀是否正确

---

## 文件清单

```
kanban-react/backend/
├── perception_agent.py          # 感知 Agent 主程序
├── perception_config.yml        # 配置文件
├── perception_routes.py         # API 路由
├── init_perception_db.py        # 数据库初始化脚本
├── start_perception_agent.sh    # 启动脚本
├── install_systemd_service.sh   # systemd 安装脚本
├── test_perception_agent.py     # 测试脚本
├── perception-agent.service     # systemd 服务文件
├── PERCEPTION_README.md         # 本文档
├── perception_agent.log         # 日志文件 (运行时生成)
└── perception_agent.pid         # PID 文件 (运行时生成)
```

---

## 数据库表结构

### perception_events 表

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INTEGER | 主键，自增 |
| event_type | TEXT | 事件类型 |
| severity | TEXT | 严重级别 (info/warning/error/critical) |
| source | TEXT | 事件来源 |
| message | TEXT | 事件消息 |
| metadata | TEXT | 元数据 (JSON) |
| timestamp | DATETIME | 事件时间 |
| hash | TEXT | 事件哈希 (去重) |
| processed | BOOLEAN | 是否已处理 |
| created_at | DATETIME | 创建时间 |
| updated_at | DATETIME | 更新时间 |

**索引**:
- `idx_perception_events_type` - 按类型查询
- `idx_perception_events_severity` - 按级别查询
- `idx_perception_events_timestamp` - 按时间排序
- `idx_perception_events_hash` - 去重查询

---

## 下一步计划

### 已完成 ✅
- [x] 创建数据库表
- [x] 集成 API 路由
- [x] 创建启动脚本
- [x] 创建 systemd 服务
- [x] 测试验证

### 待完成 📋
- [ ] 添加 Web UI 管理界面
- [ ] 实现事件自动处理策略
- [ ] 添加邮件/消息告警
- [ ] 集成更多外部数据源
- [ ] 性能优化和压力测试

---

## 联系与支持

- **项目地址**: https://github.com/mettlyz11/kanban-system
- **问题反馈**: 提交 GitHub Issue
- **文档更新**: 2026-03-11

---

**🎉 感知 Agent 系统已成功部署并运行！**
