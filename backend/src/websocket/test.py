"""
WebSocket 测试脚本
"""

import sys
import time
import socketio

# 测试配置
SERVER_URL = 'http://localhost:8086'
TEST_TOKEN = None  # 如果需要认证，设置 token


def run_test():
    """运行 WebSocket 测试"""
    print("=" * 60)
    print("WebSocket 测试")
    print("=" * 60)
    
    # 创建客户端
    sio = socketio.Client()
    
    results = {
        'connected': False,
        'authenticated': False,
        'errors': [],
    }
    
    @sio.on('connect')
    def on_connect():
        print("✅ 连接成功")
        results['connected'] = True
        
        # 发送认证事件
        auth_data = {
            'user_id': 1,
            'username': 'test_user',
        }
        if TEST_TOKEN:
            auth_data['token'] = TEST_TOKEN
        
        print(f"📤 发送认证: {auth_data}")
        sio.emit('authenticate', auth_data)
    
    @sio.on('disconnect')
    def on_disconnect():
        print("❌ 连接断开")
        results['connected'] = False
    
    @sio.on('authenticated')
    def on_authenticated(data):
        print(f"📥 收到认证响应: {data}")
        if data.get('success'):
            results['authenticated'] = True
            print("✅ 认证成功!")
        else:
            print(f"❌ 认证失败: {data.get('message')}")
    
    @sio.on('user_online')
    def on_user_online(data):
        print(f"👤 用户上线: {data}")
    
    @sio.on('online_users_list')
    def on_online_users_list(data):
        print(f"👥 在线用户列表: {data}")
    
    @sio.on('heartbeat_ack')
    def on_heartbeat_ack(data):
        print(f"💓 心跳响应: {data}")
    
    @sio.on('connect_error')
    def on_connect_error(error):
        print(f"❌ 连接错误: {error}")
        results['errors'].append(str(error))
    
    try:
        # 连接服务器
        print(f"🔌 连接到 {SERVER_URL}...")
        sio.connect(SERVER_URL, path='/socket.io', transports=['websocket', 'polling'])
        
        # 等待认证响应
        time.sleep(2)
        
        # 测试心跳
        if results['authenticated']:
            print("📤 发送心跳...")
            sio.emit('heartbeat', {'timestamp': time.time()})
            time.sleep(2)
        
        # 测试加入房间
        if results['authenticated']:
            print("📤 加入项目房间...")
            sio.emit('join_project_room', {'project_id': 1})
            time.sleep(1)
        
        # 测试锁请求
        if results['authenticated']:
            print("📤 请求编辑锁...")
            sio.emit('lock_request', {'task_id': 'test_task_1'})
            time.sleep(1)
        
        # 等待一段时间
        time.sleep(3)
        
        # 断开连接
        print("🔌 断开连接...")
        sio.disconnect()
        
    except Exception as e:
        print(f"❌ 测试异常: {e}")
        results['errors'].append(str(e))
    
    # 输出测试结果
    print("\n" + "=" * 60)
    print("测试结果")
    print("=" * 60)
    print(f"连接成功: {'✅' if results['connected'] else '❌'}")
    print(f"认证成功: {'✅' if results['authenticated'] else '❌'}")
    
    if results['errors']:
        print(f"错误: {len(results['errors'])}")
        for error in results['errors']:
            print(f"  - {error}")
    
    # 返回退出码
    return 0 if results['authenticated'] else 1


if __name__ == '__main__':
    exit_code = run_test()
    sys.exit(exit_code)
