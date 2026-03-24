from typing import Dict, List
from fastapi import WebSocket

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        self.active_connections.setdefault(user_id, []).append(websocket)

    def disconnect(self, user_id: str, websocket: WebSocket):
        self.active_connections[user_id].remove(websocket)
        if not self.active_connections[user_id]:
            del self.active_connections[user_id]

    async def send_to_user(self, user_id: str, message: dict):
        for ws in self.active_connections.get(user_id, []):
            await ws.send_json(message)

    async def broadcast(self, message: dict):
        for sockets in self.active_connections.values():
            for ws in sockets:
                await ws.send_json(message)

manager = ConnectionManager()
