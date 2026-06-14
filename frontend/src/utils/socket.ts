/**
 * WebSocket 实时数据同步工具
 * 功能：
 * 1. WebSocket 连接管理
 * 2. 任务状态实时同步
 * 3. 在线用户状态显示
 * 4. 协作编辑锁机制
 */

import { io, Socket } from 'socket.io-client';

// ============================================
// 类型定义
// ============================================
export interface OnlineUser {
  user_id: string;
  username: string;
  connected_at: string;
  sessions: number;
}

export interface TaskLock {
  task_id: string;
  locked_by: string;
  expires_at: string;
}

export interface SocketIOConfig {
  url?: string;
  userId?: string;
  username?: string;
  onConnect?: () => void;
  onDisconnect?: () => void;
  onTaskCreated?: (task: any) => void;
  onTaskUpdated?: (task: any, changes: any) => void;
  onTaskDeleted?: (taskId: string) => void;
  onUserOnline?: (user: OnlineUser) => void;
  onUserOffline?: (user: OnlineUser) => void;
  onOnlineUsersList?: (users: OnlineUser[]) => void;
  onLockAcquired?: (lock: TaskLock) => void;
  onLockDenied?: (lock: TaskLock) => void;
  onLockReleased?: (taskId: string) => void;
}

// ============================================
// SocketIO 管理类
// ============================================
class SocketIOManager {
  private socket: Socket | null = null;
  private connected = false;
  private userId: string = '';
  private username: string = '';
  private heartbeatInterval: number | null = null;
  private config: SocketIOConfig | null = null;

  /**
   * 初始化 WebSocket 连接
   */
  connect(config: SocketIOConfig): Promise<boolean> {
    return new Promise((resolve, reject) => {
      this.config = config;
      this.userId = config.userId || 'anonymous';
      this.username = config.username || '访客';

      const url = config.url || window.location.origin;
      
      console.log('🔌 正在连接 WebSocket:', url);

      try {
        this.socket = io(url, {
          path: '/socket.io',
          transports: ['websocket', 'polling'],
          query: {
            user_id: this.userId,
            username: this.username
          },
          reconnection: true,
          reconnectionDelay: 1000,
          reconnectionDelayMax: 5000,
          reconnectionAttempts: Infinity,
          timeout: 10000
        });

        // 连接成功 / 重连成功
        const onConnected = () => {
          console.log('✅ WebSocket 连接成功');
          this.connected = true;
          
          if (config.onConnect) {
            config.onConnect();
          }

          // 启动心跳
          this.startHeartbeat();
        };

        this.socket.on('connect', onConnected);
        
        // Resolve immediately once connected; errors won't reject (auto-reconnect handles them)
        let resolved = false;
        this.socket.on('connect', () => {
          if (!resolved) { resolved = true; resolve(true); }
        });
        
        // Timeout fallback: resolve anyway after 15s (let auto-reconnect work in background)
        setTimeout(() => {
          if (!resolved) {
            resolved = true;
            console.warn('⚠️ WebSocket 连接超时，后台继续重试');
            resolve(false);
          }
        }, 15000);

        // 连接断开
        this.socket.on('disconnect', () => {
          console.log('❌ WebSocket 断开连接');
          this.connected = false;
          this.stopHeartbeat();
          
          if (config.onDisconnect) {
            config.onDisconnect();
          }
        });

        // 连接错误 (socket.io 会自动重连，不要 reject)
        this.socket.on('connect_error', (error) => {
          console.warn('⚠️ WebSocket 连接错误 (自动重连中):', error.message);
          this.connected = false;
          // 不停止心跳，重连成功后会自动重启
        });

        // 重连失败
        this.socket.on('reconnect_failed', () => {
          console.error('❌ WebSocket 重连失败');
          this.connected = false;
          this.stopHeartbeat();
        });

        // 重连成功
        this.socket.on('reconnect', (attemptNumber: number) => {
          console.log('✅ WebSocket 重连成功 (尝试了 ' + attemptNumber + ' 次)');
          this.connected = true;
          if (config.onConnect) {
            config.onConnect();
          }
          this.startHeartbeat();
        });

        // 任务事件
        this.socket.on('task_created', (data) => {
          console.log('📝 任务创建:', data);
          if (config.onTaskCreated) {
            config.onTaskCreated(data.task);
          }
        });

        this.socket.on('task_updated', (data) => {
          console.log('📝 任务更新:', data);
          if (config.onTaskUpdated) {
            config.onTaskUpdated(data.task, data.changes);
          }
        });

        this.socket.on('task_deleted', (data) => {
          console.log('📝 任务删除:', data);
          if (config.onTaskDeleted) {
            config.onTaskDeleted(data.task_id);
          }
        });

        // 用户在线事件
        this.socket.on('user_online', (data) => {
          console.log('👤 用户上线:', data);
          if (config.onUserOnline) {
            config.onUserOnline(data);
          }
        });

        this.socket.on('user_offline', (data) => {
          console.log('👤 用户下线:', data);
          if (config.onUserOffline) {
            config.onUserOffline(data);
          }
        });

        this.socket.on('online_users_list', (data) => {
          console.log('👥 在线用户列表:', data);
          if (config.onOnlineUsersList) {
            config.onOnlineUsersList(data.users);
          }
        });

        // 编辑锁事件
        this.socket.on('lock_acquired', (data) => {
          console.log('🔒 锁获取:', data);
          if (config.onLockAcquired) {
            config.onLockAcquired(data);
          }
        });

        this.socket.on('lock_denied', (data) => {
          console.log('🔒 锁拒绝:', data);
          if (config.onLockDenied) {
            config.onLockDenied(data);
          }
        });

        this.socket.on('lock_released', (data) => {
          console.log('🔓 锁释放:', data);
          if (config.onLockReleased) {
            config.onLockReleased(data.task_id);
          }
        });

      } catch (error) {
        console.error('❌ 创建 WebSocket 连接失败:', error);
        reject(error);
      }
    });
  }

  /**
   * 断开连接
   */
  disconnect() {
    this.stopHeartbeat();
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
      this.connected = false;
      console.log('🔌 WebSocket 已断开');
    }
  }

  /**
   * 检查连接状态
   */
  isConnected(): boolean {
    return this.connected && this.socket !== null;
  }

  /**
   * 发送任务创建事件
   */
  emitTaskCreated(task: any) {
    if (this.socket && this.connected) {
      this.socket.emit('task_created', { task });
    }
  }

  /**
   * 发送任务更新事件
   */
  emitTaskUpdated(task: any, changes: any) {
    if (this.socket && this.connected) {
      this.socket.emit('task_updated', { task, changes });
    }
  }

  /**
   * 发送任务删除事件
   */
  emitTaskDeleted(taskId: string) {
    if (this.socket && this.connected) {
      this.socket.emit('task_deleted', { task_id: taskId });
    }
  }

  /**
   * 请求编辑锁
   */
  requestLock(taskId: string) {
    if (this.socket && this.connected) {
      this.socket.emit('lock_request', { task_id: taskId });
    }
  }

  /**
   * 释放编辑锁
   */
  releaseLock(taskId: string) {
    if (this.socket && this.connected) {
      this.socket.emit('unlock_request', { task_id: taskId });
    }
  }

  /**
   * 加入项目房间
   */
  joinProjectRoom(projectId: string) {
    if (this.socket && this.connected) {
      this.socket.emit('join_project_room', { project_id: projectId });
    }
  }

  /**
   * 离开项目房间
   */
  leaveProjectRoom(projectId: string) {
    if (this.socket && this.connected) {
      this.socket.emit('leave_project_room', { project_id: projectId });
    }
  }

  /**
   * 启动心跳
   */
  private startHeartbeat() {
    this.stopHeartbeat();
    
    this.heartbeatInterval = window.setInterval(() => {
      if (this.socket && this.connected) {
        this.socket.emit('heartbeat', { timestamp: Date.now() });
      }
    }, 30000); // 30 秒心跳
  }

  /**
   * 停止心跳
   */
  private stopHeartbeat() {
    if (this.heartbeatInterval) {
      clearInterval(this.heartbeatInterval);
      this.heartbeatInterval = null;
    }
  }

  /**
   * 通用事件监听
   */
  on(event: string, callback: (...args: any[]) => void) {
    if (this.socket) {
      this.socket.on(event, callback);
    }
  }

  /**
   * 通用事件发射
   */
  emit(event: string, data: any) {
    if (this.socket && this.connected) {
      this.socket.emit(event, data);
    }
  }

  /**
   * 移除事件监听
   */
  off(event: string, callback?: (...args: any[]) => void) {
    if (this.socket) {
      this.socket.off(event, callback);
    }
  }
}

// ============================================
// 导出单例
// ============================================
export const socketIO = new SocketIOManager();

export default socketIO;
