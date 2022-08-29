from typing import List
import fastapi as _fastapi

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[_fastapi.WebSocket] = []
    
    async def connect(self, incoming: _fastapi.WebSocket):
        await incoming.accept()
        self.active_connections.append(incoming)

    async def disconnect(self, outgoing):
        self.active_connections.remove(outgoing)
    
    async def broadcast(self, data):
        for conn in self.active_connections:
            await conn.send_text(data)

manager = ConnectionManager()