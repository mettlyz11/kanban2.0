with open('/opt/kanban-react/backend/monitor_relay.py') as f:
    c = f.read()

old = '''async def upstream_handler(websocket):
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
        macmini_clients.discard(websocket)
        logger.info(f"🖥️ Mac mini 已断开 (共 {len(macmini_clients)} 个)")'''

new = '''async def upstream_handler(websocket):
    """处理 Mac mini 监控服务的连接（支持多上游）"""
    macmini_clients.add(websocket)
    logger.info(f"🖥️ Mac mini 已连接 (共 {len(macmini_clients)} 个)")
    
    try:
        async for message in websocket:
            await forward_to_clients(message)
    except websockets.ConnectionClosed:
        pass
    finally:
        macmini_clients.discard(websocket)
        logger.info(f"🖥️ Mac mini 已断开 (共 {len(macmini_clients)} 个)")'''

if old in c:
    c = c.replace(old, new)
    with open('/opt/kanban-react/backend/monitor_relay.py', 'w') as f:
        f.write(c)
    # print('OK: upstream_handler fixed')
else:
    # print('ERROR: old block not found')
    import difflib
    # find similar
    for line in c.split('\n'):
        if 'global macmini_ws' in line:
            pass  # previously printed matching line
