# 🚀 实时数据同步功能 - 快速使用指南

## 📦 安装和部署

### 1. 后端部署（服务器）

```bash
# SSH 登录服务器
ssh -i ~/.ssh/aliyun_macmini.pem root@47.93.184.128

# 停止现有服务
cd /opt/kanban-react
bash start.sh

# 验证服务状态
ps aux | grep 'python.*app.py'
tail -50 /var/log/kanban_backend.log
```

### 2. 前端部署

```bash
# 安装依赖
cd /opt/kanban-react/frontend
npm install socket.io-client --save

# 构建生产版本
npm run build

# 上传文件（从本地）
scp frontend/src/utils/socket.ts root@47.93.184.128:/opt/kanban-react/frontend/src/utils/
scp frontend/src/components/OnlineUsers.tsx root@47.93.184.128:/opt/kanban-react/frontend/src/components/
scp frontend/src/components/EditLockIndicator.tsx root@47.93.184.128:/opt/kanban-react/frontend/src/components/
```

### 3. Nginx 配置

```bash
# 备份原配置
cp /etc/nginx/nginx.conf /etc/nginx/nginx.conf.bak

# 更新配置（已自动配置）
nginx -t && nginx -s reload
```

## 🔌 WebSocket 连接测试

### 方法 1: 浏览器测试页
访问：http://47.93.184.128/test_websocket.html

1. 点击"连接"按钮
2. 查看状态变为"✅ 已连接"
3. 点击"发送任务事件"测试广播
4. 点击"请求编辑锁"测试锁机制

### 方法 2: 浏览器控制台
```javascript
// 打开浏览器控制台 (F12)
const socket = io(window.location.origin, {
  path: '/socket.io',
  transports: ['websocket', 'polling']
});

socket.on('connect', () => console.log('✅ 连接成功:', socket.id));
socket.on('disconnect', () => console.log('❌ 断开连接'));
socket.on('user_online', (data) => console.log('👤 用户上线:', data));
```

## 💻 前端集成示例

### 在 React 组件中使用

```tsx
import React, { useEffect, useState } from 'react';
import { socketIO, OnlineUser } from './utils/socket';
import OnlineUsers from './components/OnlineUsers';
import EditLockIndicator from './components/EditLockIndicator';

function TaskBoard() {
  const [tasks, setTasks] = useState([]);
  const currentUserId = 'user123';

  useEffect(() => {
    // 初始化 WebSocket 连接
    socketIO.connect({
      url: window.location.origin,
      userId: currentUserId,
      username: '张三',
      onConnect: () => console.log('✅ WebSocket 已连接'),
      onDisconnect: () => console.log('❌ WebSocket 已断开'),
      onTaskCreated: (task) => {
        setTasks(prev => [...prev, task]);
      },
      onTaskUpdated: (task, changes) => {
        setTasks(prev => prev.map(t => 
          t.id === task.id ? { ...t, ...changes } : t
        ));
      },
      onTaskDeleted: (taskId) => {
        setTasks(prev => prev.filter(t => t.id !== taskId));
      },
      onOnlineUsersList: (users) => {
        console.log('👥 在线用户:', users);
      }
    });

    // 清理
    return () => {
      socketIO.disconnect();
    };
  }, [currentUserId]);

  // 创建任务时广播
  const handleCreateTask = (task) => {
    // 本地更新
    setTasks(prev => [...prev, task]);
    // 广播给其他用户
    socketIO.emitTaskCreated(task);
  };

  // 更新任务时广播
  const handleUpdateTask = (task, changes) => {
    // 本地更新
    setTasks(prev => prev.map(t => 
      t.id === task.id ? { ...t, ...changes } : t
    ));
    // 广播给其他用户
    socketIO.emitTaskUpdated(task, changes);
  };

  return (
    <div>
      {/* 显示在线用户 */}
      <OnlineUsers currentUserId={currentUserId} />

      {/* 任务列表 */}
      {tasks.map(task => (
        <div key={task.id}>
          <h3>{task.title}</h3>
          
          {/* 编辑锁指示器 */}
          <EditLockIndicator
            taskId={task.id}
            userId={currentUserId}
            onLockChange={(locked) => {
              // 被锁定时禁用编辑
            }}
          />
          
          {/* 任务内容 */}
          <p>{task.description}</p>
        </div>
      ))}
    </div>
  );
}
```

## 🔒 编辑锁使用示例

```tsx
import { useState } from 'react';
import EditLockIndicator from './components/EditLockIndicator';

function TaskEditor({ taskId, userId }) {
  const [isEditable, setIsEditable] = useState(false);

  const handleLockChange = (locked) => {
    // locked=true 表示被锁定（可能是自己或他人）
    // locked=false 表示未锁定，可以编辑
    setIsEditable(!locked);
  };

  return (
    <div>
      <EditLockIndicator
        taskId={taskId}
        userId={userId}
        onLockChange={handleLockChange}
      />
      
      <textarea
        disabled={!isEditable}
        placeholder={isEditable ? '编辑任务...' : '任务被锁定，无法编辑'}
      />
    </div>
  );
}
```

## 📊 事件类型参考

### 客户端 → 服务器
| 事件名 | 参数 | 说明 |
|--------|------|------|
| `task_created` | `{ task: Task }` | 任务创建 |
| `task_updated` | `{ task: Task, changes: Object }` | 任务更新 |
| `task_deleted` | `{ task_id: string }` | 任务删除 |
| `lock_request` | `{ task_id: string }` | 请求编辑锁 |
| `unlock_request` | `{ task_id: string }` | 释放编辑锁 |
| `heartbeat` | `{ timestamp: number }` | 心跳 |
| `join_project_room` | `{ project_id: string }` | 加入项目房间 |

### 服务器 → 客户端
| 事件名 | 数据 | 说明 |
|--------|------|------|
| `task_created` | `{ task, created_by }` | 任务创建通知 |
| `task_updated` | `{ task, changes, updated_by }` | 任务更新通知 |
| `task_deleted` | `{ task_id, deleted_by }` | 任务删除通知 |
| `user_online` | `{ user_id, username, online_count }` | 用户上线 |
| `user_offline` | `{ user_id, username, online_count }` | 用户下线 |
| `online_users_list` | `{ users: OnlineUser[] }` | 在线用户列表 |
| `lock_acquired` | `{ task_id, locked_by, expires_at }` | 锁获取成功 |
| `lock_denied` | `{ task_id, locked_by, locked_at }` | 锁请求被拒绝 |
| `lock_released` | `{ task_id, released_by }` | 锁释放通知 |

## 🐛 故障排查

### WebSocket 连接失败
```bash
# 检查后端服务
ps aux | grep 'python.*app.py'
tail -100 /var/log/kanban_backend.log

# 检查 Nginx 配置
nginx -t
cat /etc/nginx/nginx.conf | grep -A 15 'socket.io'

# 检查防火墙
iptables -L -n | grep 80
```

### 编辑锁不工作
```javascript
// 检查锁事件监听
socketIO.on('lock_acquired', (lock) => {
  console.log('✅ 锁获取:', lock);
});

socketIO.on('lock_denied', (lock) => {
  console.log('❌ 锁拒绝:', lock);
});
```

### 在线用户不显示
```javascript
// 检查在线用户事件
socketIO.on('online_users_list', (data) => {
  console.log('👥 在线用户:', data.users);
});
```

## 📞 技术支持

- **文档**: `/opt/kanban-react/REALTIME_SYNC_REPORT.md`
- **日志**: `/var/log/kanban_backend.log`
- **测试页**: http://47.93.184.128/test_websocket.html

---

**版本**: v3.1.0  
**更新日期**: 2026-03-23
