#!/usr/bin/env python3
"""Standalone socket.io server - runs on port 8089 with eventlet."""
import os, sys
sys.path.insert(0, '/opt/kanban-react/backend')
os.chdir('/opt/kanban-react/backend')

from flask import Flask
from src.websocket.index import init_socketio, _register_handlers
from flask_socketio import SocketIO

app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24).hex()

# Only init socketio - no DB, no routes, no perceptions
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode='eventlet',
    ping_timeout=60,
    ping_interval=25,
    max_http_buffer_size=1e8,
    path='/socket.io',
    logger=False,
    engineio_logger=False,
)

from src.websocket.events import set_socketio
set_socketio(socketio)
_register_handlers(socketio)
# print(f"✅ Socket.IO standalone server ready on port 8091")

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=8091, debug=False)
