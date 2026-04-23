# 🎯 感知Agent (Perception Agent) 使用说明

## 概述

感知Agent是一个智能监听与分析系统，能够实时监控系统日志、API错误、性能指标和用户行为，智能分析并触发相应的响应动作。

## 系统架构

```
事件源 → 监听器 → 过滤器 → 分析器 → 触发器 → 响应动作
```

### 事件源
- 系统日志（看板、T109、Pepi等）
- 错误报告（5xx错误、异常堆栈）
- 性能指标（CPU、内存、响应时间）
- 用户行为（操作频率、重复操作）

### 监听器
1. **LogListener** - 实时读取日志文件
2. **ErrorListener** - API和系统错误检测
3. **MetricListener** - 系统性能指标采集
4. **BehaviorListener** - 用户行为分析

### 严重程度分级
- **Critical** - 立即触发长思考
- **High** - 1小时内触发反思
- **Medium** - 每日汇总
- **Low** - 周度改进

## 文件结构

```
kanban-react/backend/
├── perception_agent.py       # 核心模块
├── perception_config.yml     # 配置文件
└── app.py                    # 已集成感知Agent

kanban-react/frontend/src/
├── pages/
│   └── Perception.tsx        # 前端状态页面
├── components/
│   └── Layout.tsx            # 已添加菜单
└── App.tsx                   # 已添加路由
```

## API端点

### 获取Agent状态
```
GET /api/perception/status
```

### 获取事件日志
```
GET /api/perception/events
```

### 发送测试事件
```
POST /api/perception/test
Body: {
  "type": "test",
  "message": "测试消息"
}
```

### 获取配置
```
GET /api/perception/config
```

### 记录用户行为
```
POST /api/perception/record-action
Body: {
  "user_id": "user123",
  "action": "create_task",
  "target": "task_456"
}
```

## 配置说明

配置文件位置: `kanban-react/backend/perception_config.yml`

### 日志监听器配置
```yaml
log_watcher:
  enabled: true
  files:
    - ~/.openclaw/workspace/kanban-react/server.log
    - ~/.openclaw/workspace/logs/kanban_v5.log
  patterns:
    - regex: "ERROR|CRITICAL|FATAL"
      severity: critical
      action: immediate_reflection
```

### 性能指标配置
```yaml
metric_watcher:
  enabled: true
  metrics:
    - name: cpu_usage
      threshold: 80    # CPU使用率超过80%告警
      duration: 300    # 持续5分钟
    - name: memory_usage
      threshold: 85
      duration: 300
```

### 行为监听配置
```yaml
behavior_watcher:
  enabled: true
  patterns:
    - name: repeated_action
      window: 300      # 5分钟窗口
      count: 3         # 重复3次触发
      action: suggest_optimization
```

## 前端页面

访问: `http://localhost:5173/perception` (开发环境)

功能：
- 📊 实时状态监控
- 📋 事件日志查看（支持按严重级别筛选）
- ⚙️ 配置信息展示
- 🧪 测试工具

## 使用方式

### 1. 自动启动
感知Agent会在看板后端启动时自动启动：
```bash
cd kanban-react/backend
python3 app.py
```

### 2. 独立运行
也可以独立运行感知Agent：
```bash
cd kanban-react/backend
python3 perception_agent.py
```

### 3. 在代码中记录事件
```python
from perception_agent import get_agent

agent = get_agent()
if agent:
    # 记录API错误
    agent.record_api_error(
        status_code=500,
        endpoint='/api/test',
        error_message='Something went wrong'
    )
    
    # 记录用户行为
    agent.record_action(
        user_id='user123',
        action='delete_project',
        target='project_456'
    )
```

## 日志存储

事件日志存储位置：
```
~/.openclaw/workspace/logs/perception/
├── critical_202602.log   # Critical级别事件
├── high_202602.log       # High级别事件
├── medium_202602.log     # Medium级别事件
├── low_202602.log        # Low级别事件
└── alert_202602.log      # 告警事件
```

## 故障排查

### Agent无法启动
1. 检查配置文件是否存在: `perception_config.yml`
2. 检查日志目录权限: `~/.openclaw/workspace/logs/perception`
3. 查看Python错误信息

### 监听器不工作
1. 检查配置文件中的`enabled`设置
2. 检查日志文件路径是否正确
3. 查看Agent状态页面

### 事件未记录
1. 检查去重机制（相同事件5分钟内不重复触发）
2. 检查过滤器配置
3. 查看事件日志文件

## 未来扩展

计划添加的功能：
- [ ] 外部监听器（GitHub、arXiv）
- [ ] 自动修复动作
- [ ] 知识库存储
- [ ] 告警通知（邮件、消息）
- [ ] WebSocket实时推送
