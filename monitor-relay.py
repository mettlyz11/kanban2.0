#!/usr/bin/env python3
"""
系统监控 WebSocket 中继服务
部署在阿里云服务器上 (47.93.184.128:8765)

架构：
  Mac mini 监控服务 ──ws://47.93.184.128:8765/upstream──▶ 中继服务
  前端 React App    ──ws://47.93.184.128:8765/──────────▶ 中继服务
  
中继负责将 Mac mini 的数据转发给所有前端客户端
"""

import json
import asyncio
import websockets
from websockets.server import serve

# 前端客户端列表
frontend_clients = set()

# Mac mini 上游连接
macmini_ws = None

async def handler(websocket, path):
    global macmini_ws
    
    if path == "/upstream":
        # Mac mini 监控服务连接
        macmini_ws = websocket
        print("🖥️ Mac mini 已连接")
        try:
            async for message in websocket:
                # 转发给所有前端
                if frontend_clients:
                    websockets.broadcast(frontend_clients, message)
        except websockets.ConnectionClosed:
            pass
        finally:
            macmini_ws = None
            print("🖥️ Mac mini 已断开")
    
    else:
        # 前端客户端连接
        frontend_clients.add(websocket)
        print(f"📱 前端已连接 (共 {len(frontend_clients)} 个)")
        
        # 发送状态
        await websocket.send(json.dumps({
            "type": "status",
            "upstream_connected": macmini_ws is not None
        }))
        
        try:
            async for message in websocket:
                # 前端消息转发给 Mac mini
                if macmini_ws and macmini_ws.open:
                    await macmini_ws.send(message)
        except websockets.ConnectionClosed:
            pass
        finally:
            frontend_clients.discard(websocket)
            print(f"📱 前端已断开 (共 {len(frontend_clients)} 个)")

async def main():
    print("🔄 监控中继服务启动: ws://0.0.0.0:8765")
    print("   上游路径: /upstream (Mac mini 连接)")
    print("   下游路径: /        (前端连接)")
    
    async with serve(handler, "0.0.0.0", 8765):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
