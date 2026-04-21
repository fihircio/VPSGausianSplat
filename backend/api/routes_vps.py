import asyncio
import json
import logging
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from backend.api.schemas import EvaluationResponse, LocalizeResponse, AgentPoseUpdate
from backend.services.vps import VPSService
from backend.services.sync_service import sync_manager
from backend.utils.config import get_settings
from backend.utils.db import get_db
from backend.utils.storage import save_upload, get_storage

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/vps", tags=["vps"])


@router.post("/localize", response_model=LocalizeResponse)
async def localize(
    scene_id: str = Form(...),
    query_image: UploadFile = File(...),
    agent_id: str | None = Form(None),
    db: Session = Depends(get_db),
) -> LocalizeResponse:
    settings = get_settings()
    query_path = save_upload(query_image, f"queries/{scene_id}")
    try:
        result = VPSService.localize(scene_id=scene_id, query_image_path=query_path, db=db)
        logger.info(f"Localize result type: {type(result)}")
        logger.info(f"Localize result: {result}")
        # Broadcast to other users if agent_id is provided
        if agent_id:
            await sync_manager.broadcast(scene_id, {
                "type": "agent_update",
                "agent_id": agent_id,
                "position": result["position"],
                "rotation": result["rotation"]
            })
            
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        logger.exception("Unexpected error during localization")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}") from e

    return LocalizeResponse(**result)


@router.websocket("/ws/agents/{scene_id}")
async def agent_sync_websocket(websocket: WebSocket, scene_id: str):
    """
    WebSocket endpoint for real-time spatial sync.
    """
    await sync_manager.connect(scene_id, websocket)
    
    # 1. Send initial state to the new client
    initial_state = sync_manager.get_scene_state(scene_id)
    if initial_state:
        await websocket.send_text(json.dumps({
            "type": "initial_state",
            "agents": initial_state
        }, default=str))

    try:
        while True:
            # 2. Prune if no message/heartbeat for 60s
            data = await asyncio.wait_for(websocket.receive_text(), timeout=60.0)
            try:
                msg = json.loads(data)
                if msg.get("type") == "pose_update":
                    # Broadcast the pose update to all clients in the scene
                    # The broadcast method will also update the persistent state
                    broadcast_msg = {**msg, "type": "agent_update"}
                    await sync_manager.broadcast(scene_id, broadcast_msg)
            except Exception as e:
                logger.error(f"Sync message error: {e}")
    except WebSocketDisconnect:
        sync_manager.disconnect(scene_id, websocket)
    except asyncio.TimeoutError:
        logger.warning(f"WebSocket timeout for scene {scene_id}")
        sync_manager.disconnect(scene_id, websocket)


@router.get("/evaluation/{scene_id}", response_model=EvaluationResponse)
def get_evaluation(scene_id: str) -> EvaluationResponse:
    storage = get_storage()
    report_remote = "debug/vps_evaluation_report.json"
    
    if not storage.exists(report_remote):
        raise HTTPException(status_code=404, detail="Evaluation report not found")
    
    local_report = storage.ensure_local_copy(report_remote)
    with local_report.open("r") as f:
        data = json.load(f)
    
    if data.get("scene_id") != scene_id:
        raise HTTPException(status_code=404, detail=f"No evaluation records for scene {scene_id}")

    best = data.get("best_config", {})
    return EvaluationResponse(
        summary=best.get("summary"),
        config=best.get("config")
    )
