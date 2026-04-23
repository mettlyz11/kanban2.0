#!/usr/bin/env python3
"""
更新 app.py 集成 Flask-SocketIO
"""

import re

# 读取原始文件
with open('/opt/kanban-react/backend/app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 更新 Flask 导入，添加 Flask-SocketIO
old_imports = """from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS"""

new_imports = """from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit"""

content = content.replace(old_imports, new_imports)

# 2. 在 CORS(app) 后添加 SocketIO 初始化
old_cors_line = "CORS(app)"
new_socketio_init = """CORS(app)

# ============================================
# WebSocket 实时数据同步配置
# ============================================
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode='eventlet',
    ping_timeout=60,
    ping_interval=25,
    max_http_buffer_size=1e8,
    path='/socket.io'
)
logger.info("✅ Flask-SocketIO 已初始化")"""

content = content.replace(old_cors_line, new_socketio_init)

# 3. 在文件末尾前添加 SocketIO 事件注册和运行配置
# 找到 if __name__ == '__main__' 部分
if "__main__" in content:
    # 在 if __name__ 之前添加事件注册
    socketio_registration = """
# ============================================
# 注册 WebSocket 事件处理器
# ============================================
try:
    from socket_events import register_socket_events
    register_socket_events(socketio)
    logger.info("✅ WebSocket 事件处理器已注册")
except ImportError as e:
    logger.warning(f"⚠️ WebSocket 事件处理器导入失败：{e}")

"""
    
    # 找到最后一个 if __name__ 块
    main_pattern = r"(\nif __name__ == ['\"]__main__['\"]:)"
    match = re.search(main_pattern, content)
    if match:
        insert_pos = match.start()
        content = content[:insert_pos] + socketio_registration + content[insert_pos:]
    
    # 更新 app.run 为 socketio.run
    old_run = "app.run(host='0.0.0.0', port=8086, debug=False)"
    new_run = """# 使用 socketio.run 替代 app.run 以支持 WebSocket
# app.run(host='0.0.0.0', port=8086, debug=False)
socketio.run(app, host='0.0.0.0', port=8086, debug=False, allow_unsafe_werkzeug=True)"""
    
    content = content.replace(old_run, new_run)

# 写入更新后的文件
with open('/opt/kanban-react/backend/app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("✅ app.py 更新完成")
