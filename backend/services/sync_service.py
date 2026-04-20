import json
import logging
from typing import Dict, List, Set
from fastapi import WebSocket

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        # Map scene_id -> Set of active WebSockets
        self.active_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, scene_id: str, websocket: WebSocket):
        await websocket.accept()
        if scene_id not in self.active_connections:
            self.active_connections[scene_id] = set()
        self.active_connections[scene_id].add(websocket)
        logger.info(f"New connection to scene {scene_id}. Total: {len(self.active_connections[scene_id])}")

    def disconnect(self, scene_id: str, websocket: WebSocket):
        if scene_id in self.active_connections:
            self.active_connections[scene_id].remove(websocket)
            if not self.active_connections[scene_id]:
                del self.active_connections[scene_id]
        logger.info(f"Connection left scene {scene_id}")

    async def broadcast(self, scene_id: str, message: dict):
        if scene_id not in self.active_connections:
            return
        
        # Serialization helper
        data = json.dumps(message, default=str)
        
        # Broadcast to all attendees
        disconnected = set()
        for connection in self.active_connections[scene_id]:
            try:
                await connection.send_text(data)
            except Exception:
                disconnected.add(connection)
        
        # Cleanup broken connections
        for conn in disconnected:
            self.disconnect(scene_id, conn)

# Global manager instance
sync_manager = ConnectionManager()
