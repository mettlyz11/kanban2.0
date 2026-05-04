"""
WebSocket 测试客户端 - 使用 socket.io-client
"""

import sys
import time
import socketio

# 测试配置
SERVER_URL = 'http://localhost:8086'


def run_test():
    """运行 WebSocket 测试"""
    print("=" * 60)
    print("WebSocket 测试客户端")
    print("=" * 60)
    
    sio = socketio.Client()
    
    results = {
        'connected': False,
        'authenticated': False,
        'heartbeat_received': False,
        'errors': [],
    }
    
    @sio.on('connect')
    def on_connect():
        print("✅ 已连接到服务器")
        results['connected'] = True
        
        # 发送认证
        print("📤 发送 authenticate 事件...")
        sio.emit('authenticate', {
            'user_id': 1,
            'username': 'test_user',
        })
    
    @sio.on('disconnect')
    def on_disconnect():
        print("❌ 连接断开")
    
    @sio.on('authenticated')
    def on_authenticated(data):
        print(f"📥 收到 authenticated: {data}")
        if data.get('success'):
            results['authenticated'] = True
            print("✅ 认证成功!")
        else:
            print(f"❌ 认证失败: {data.get('message')}")
    
    @sio.on('user_online')
    def on_user_online(data):
        print(f"👤 user_online: {data.get('username')} 上线")
    
    @sio.on('online_users_list')
    def on_online_users_list(data):
        users = data.get('users', [])
        print(f"👥 在线用户: {len(users)} 人")
    
    @sio.on('heartbeat_ack')
    def on_heartbeat_ack(data):
        print(f"💓 heartbeat_ack: {data}")
        results['heartbeat_received'] = True
    
    @sio.on('connect_error')
    def on_connect_error(error):
        print(f"❌ 连接错误: {error}")
        results['errors'].append(str(error))
    
    @sio.on('lock_acquired')
    def on_lock_acquired(data):
        print(f"🔒 lock_acquired: {data}")
    
    @sio.on('lock_denied')
    def on_lock_denied(data):
        print(f"🔒 lock_denied: {data}")
    
    @sio.on('lock_released')
    def on_lock_released(data):
        print(f"🔓 lock_released: {data}")
    
    try:
        # 连接
        print(f"🔌 连接到 {SERVER_URL}...")
        sio.connect(
            SERVER_URL,
            socketio_path='/socket.io',
            transports=['websocket', 'polling']
        )
        
        # 等待认证
        time.sleep(2)
        
        if results['authenticated']:
            # 测试心跳
            print("📤 发送 heartbeat...")
            sio.emit('heartbeat', {'timestamp': time.time()})
            time.sleep(2)
            
            # 测试加入房间
            print("📤 发送 join_project_room...")
            sio.emit('join_project_room', {'project_id': 1})
            time.sleep(1)
            
            # 测试锁
            print("📤 发送 lock_request...")
            sio.emit('lock_request', {'task_id': 'test_task_1'})
            time.sleep(1)
            
            # 等待
            time.sleep(2)
        
        # 断开
        print("🔌 断开连接...")
        sio.disconnect()
        
    except Exception as e:
        print(f"❌ 异常: {e}")
        results['errors'].append(str(e))
    
    # 结果
    print("\n" + "=" * 60)
    print("测试结果")
    print("=" * 60)
    print(f"连接: {'✅' if results['connected'] else '❌'}")
    print(f"认证: {'✅' if results['authenticated'] else '❌'}")
    print(f"心跳: {'✅' if results['heartbeat_received'] else '❌'}")
    
    if results['errors']:
        print(f"\n错误 ({len(results['errors'])}):")
        for err in results['errors']:
            print(f"  - {err}")
    
    return 0 if results['authenticated'] else 1


if __name__ == '__main__':
    sys.exit(run_test())
