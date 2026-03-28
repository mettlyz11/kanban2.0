# 看板系统更新日志

## v3.1.0 (2026-03-23) - 实时数据同步功能

### 🎉 新增功能

#### WebSocket 实时数据同步
- ✅ 集成 Flask-SocketIO 后端
- ✅ 实现 WebSocket 连接管理
- ✅ 任务状态实时同步（创建/更新/删除）
- ✅ 在线用户状态显示
- ✅ 协作编辑锁机制

#### 后端改进
- 新增 `socket_events.py` 模块处理 WebSocket 事件
- 支持多端登录和会话管理
- 编辑锁超时自动释放（5 分钟）
- 心跳检测机制（30 秒间隔）

#### 前端组件
- 新增 `OnlineUsers` 组件显示在线用户
- 新增 `EditLockIndicator` 组件显示编辑锁状态
- 新增 `socket.ts` WebSocket 工具类

### 🔧 技术栈
- Flask-SocketIO 5.3.6
- Socket.IO Client 4.7.2
- Eventlet 0.34.2 (异步模式)

### 📝 配置变更
- Nginx 添加 WebSocket 代理支持
- 后端启动方式改为 `socketio.run()`
- 数据库连接池配置优化

### 🧪 测试
- WebSocket 连接测试通过
- 多客户端实时同步测试通过
- 编辑锁机制测试通过

---

## v3.0.0 (2026-03-20) - 初始版本
- 基础看板功能
- 任务管理
- 项目管理
- 用户认证
