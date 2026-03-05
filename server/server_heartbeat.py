import asyncio
from datetime import datetime
from .websocket_manager import manager

SERVER_PING_INTERVAL = 10  # seconds
SERVER_PONG_TIMEOUT = 30   # seconds

async def server_heartbeat():
    """Periodically send ping to all clients and close dead connections."""
    while True:
        await asyncio.sleep(SERVER_PING_INTERVAL)
        now = datetime.now()
        # Copy connections to avoid holding lock during async ops
        async with manager._session_lock:
            connections = list(manager.connections.items())
        for user_id, ws in connections:
            try:
                await ws.send_json({"type": "ping"})
                # Mark ping sent time
                await manager.update_session(user_id, last_ping=now)
            except Exception:
                # If sending fails, disconnect
                await manager.disconnect(user_id)
                continue
            # Check for pong timeout
            session = manager.get_session(user_id)
            last_pong = getattr(session, "last_pong", None)
            last_ping = getattr(session, "last_ping", None)
            if last_ping and (not last_pong or (now - last_pong).total_seconds() > SERVER_PONG_TIMEOUT):
                await manager.disconnect(user_id)
