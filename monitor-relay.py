#!/usr/bin/env python3
"""
系统监控 WebSocket 中继服务
部署在阿里云服务器上 (47.93.184.128:8765)

架构：
  Mac mini 监控服务 ──ws://47.93.184.128/monitor/upstream──▶ 中继服务
  前端 React App    ──ws://47.93.184.128/monitor/──────────▶ 中继服务
"""

import json
import asyncio
import logging
import websockets
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# 前端客户端列表
frontend_clients = set()

# Mac mini 上游连接
macmini_ws = None

async def forward_to_clients(message):
    """转发数据给所有前端客户端"""
    if frontend_clients:
        websockets.broadcast(frontend_clients, message)

async def upstream_handler(websocket):
    """处理 Mac mini 监控服务的连接"""
    global macmini_ws
    macmini_ws = websocket
    logger.info("🖥️ Mac mini 已连接")
    
    try:
        async for message in websocket:
            await forward_to_clients(message)
    except websockets.ConnectionClosed:
        pass
    finally:
        macmini_ws = None
        logger.info("🖥️ Mac mini 已断开")

async def client_handler(websocket, path):
    """处理前端客户端连接"""
    if path == "/upstream" or (hasattr(websocket, 'path') and websocket.path == "/upstream"):
        await upstream_handler(websocket)
        return
        
    frontend_clients.add(websocket)
    logger.info(f"📱 前端已连接 (共 {len(frontend_clients)} 个)")
    
    # 发送状态
    try:
        await websocket.send(json.dumps({
            "type": "status",
            "upstream_connected": macmini_ws is not None
        }))
    except:
        pass
    
    try:
        async for message in websocket:
            if macmini_ws and macmini_ws.open:
                await macmini_ws.send(message)
    except websockets.ConnectionClosed:
        pass
    finally:
        frontend_clients.discard(websocket)
        logger.info(f"📱 前端已断开 (共 {len(frontend_clients)} 个)")

async def main():
    print(f"🔄 监控中继服务启动: ws://0.0.0.0:8765")
    print(f"   上游路径: /upstream (Mac mini 连接)")
    print(f"   下游路径: /        (前端连接)")
    print(f"   时间: {datetime.now().isoformat()}")
    
    async with websockets.serve(client_handler, "0.0.0.0", 8765):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
