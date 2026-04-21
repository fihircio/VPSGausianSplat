import json
import logging
from typing import Dict, List, Set
from fastapi import WebSocket
from sqlalchemy.orm import Session
from sqlalchemy import select

from backend.models.agent import AgentSession

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        # Map scene_id -> Set of active WebSockets
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # Map scene_id -> {agent_id: last_pose}
        self.agent_states: Dict[str, Dict[str, dict]] = {}

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
                # Optional: We keep agent_states for a bit for late joiners? 
                # For now, keep it simple.
        logger.info(f"Connection left scene {scene_id}")

    def get_scene_state(self, scene_id: str) -> List[dict]:
        """Returns the list of current agent states for a scene."""
        states = self.agent_states.get(scene_id, {})
        return list(states.values())

    def persist_agent_states(self, db: Session):
        """Flush in-memory poses to the database."""
        for scene_id, agents in self.agent_states.items():
            for agent_id, state in agents.items():
                try:
                    # Try to find existing session
                    stmt = select(AgentSession).where(
                        AgentSession.scene_id == scene_id,
                        AgentSession.id == agent_id
                    )
                    session_record = db.execute(stmt).scalar_one_or_none()

                    pos = state.get("position", [0, 0, 0])
                    rot = state.get("rotation", [0, 0, 0, 1])

                    if session_record:
                        session_record.position_x = pos[0]
                        session_record.position_y = pos[1]
                        session_record.position_z = pos[2]
                        session_record.rotation_x = rot[0]
                        session_record.rotation_y = rot[1]
                        session_record.rotation_z = rot[2]
                        session_record.rotation_w = rot[3]
                    else:
                        # Create new session if not exists
                        # Note: we might not have 'name' or 'role' in the broadcast msg
                        # unless we added it to the schema.
                        new_session = AgentSession(
                            id=agent_id,
                            scene_id=scene_id,
                            name=state.get("name", "Unknown Agent"),
                            role=state.get("role", "Clinician"),
                            position_x=pos[0],
                            position_y=pos[1],
                            position_z=pos[2],
                            rotation_x=rot[0],
                            rotation_y=rot[1],
                            rotation_z=rot[2],
                            rotation_w=rot[3]
                        )
                        db.add(new_session)
                except Exception as e:
                    logger.error(f"Error persisting agent {agent_id}: {e}")
        
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to commit agent states: {e}")

    async def broadcast(self, scene_id: str, message: dict):
        if scene_id not in self.active_connections:
            return
        
        # Update internal state if this is an agent update
        if message.get("type") == "agent_update" and "agent_id" in message:
            if scene_id not in self.agent_states:
                self.agent_states[scene_id] = {}
            # Update or merge the agent state
            self.agent_states[scene_id][message["agent_id"]] = message

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
