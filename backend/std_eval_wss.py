#!/usr/bin/env python3
"""SDS STD-EVAL 实时看板 WebSocket 服务"""
import asyncio, json, os, base64, hashlib, logging
from pathlib import Path
import websockets

DATA_DIR = Path("/opt/kanban-react/backend/uploads/std-eval")
DATA_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(level=logging.INFO, format="[WS] %(message)s")
log = logging.getLogger("WS")

clients = set()
last_data = {"cycles": [], "tasks": [], "timestamp": "", "version": 0}
last_hash = ""

def load_data():
    global last_data, last_hash
    json_path = DATA_DIR / "std_eval_data.json"
    if not json_path.exists():
        return
    raw = json_path.read_text()
    h = hashlib.md5(raw.encode()).hexdigest()
    if h == last_hash:
        return
    last_hash = h
    try:
        data = json.loads(raw)
        data["version"] = last_data.get("version", 0) + 1
        last_data = data
    except:
        pass

async def handler(ws):
    clients.add(ws)
    log.info(f"Client connected ({len(clients)} total)")
    try:
        # 立即发送当前数据
        if last_data.get("cycles"):
            await ws.send(json.dumps(last_data))
        async for _ in ws:
            pass  # 保持连接，不接收消息
    except:
        pass
    finally:
        clients.discard(ws)
        log.info(f"Client disconnected ({len(clients)} remaining)")

async def broadcaster():
    while True:
        load_data()
        if last_data.get("cycles") and clients:
            msg = json.dumps(last_data)
            await asyncio.gather(*[c.send(msg) for c in clients], return_exceptions=True)
        await asyncio.sleep(5)  # 每 5s 检查一次

async def main():
    log.info("Starting STD-EVAL WebSocket server on port 18889...")
    async with websockets.serve(handler, "0.0.0.0", 18889):
        await broadcaster()

if __name__ == "__main__":
    asyncio.run(main())
