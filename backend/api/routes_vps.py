import asyncio
import json
import logging
import time
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from backend.api.auth import require_scope, SCOPE_QUERY
from backend.api.schemas import EvaluationResponse, LocalizeResponse, MultiFrameLocalizeResponse, AgentPoseUpdate
from backend.services.auth_service import AuthContext
from backend.services.vps import VPSService
from backend.services.sync_service import sync_manager
from backend.utils.config import get_settings
from backend.utils.db import get_db
from backend.utils.image import resize_if_needed
from backend.utils.storage import save_upload, get_storage
from backend.utils.metrics import record_query

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/vps", tags=["vps"])


@router.post("/localize", response_model=LocalizeResponse, dependencies=[Depends(require_scope(SCOPE_QUERY))])
async def localize(
    scene_id: str = Form(...),
    query_image: UploadFile = File(...),
    agent_id: str | None = Form(None),
    hint_position: str | None = Form(None),
    hint_radius: float | None = Form(None),
    hint_floor_height: str | None = Form(None),
    geo_hint: str | None = Form(None),
    db: Session = Depends(get_db),
) -> LocalizeResponse:
    settings = get_settings()
    query_path = save_upload(query_image, f"queries/{scene_id}")
    resize_if_needed(query_path)
    _start = time.time()
    try:
        result = VPSService.localize(
            scene_id=scene_id,
            query_image_path=query_path,
            db=db,
            hint_position=json.loads(hint_position) if hint_position else None,
            hint_radius=hint_radius or 25.0,
            hint_floor_height=json.loads(hint_floor_height) if hint_floor_height else None,
            geo_hint=json.loads(geo_hint) if geo_hint else None,
        )
        _elapsed = (time.time() - _start) * 1000
        record_query(scene_id, True, _elapsed)
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
        _elapsed = (time.time() - _start) * 1000
        record_query(scene_id, False, _elapsed)
        raise HTTPException(status_code=404, detail=str(e)) from e
    except RuntimeError as e:
        _elapsed = (time.time() - _start) * 1000
        record_query(scene_id, False, _elapsed)
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        _elapsed = (time.time() - _start) * 1000
        record_query(scene_id, False, _elapsed)
        logger.exception("Unexpected error during localization")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}") from e

    return LocalizeResponse(**result)


@router.post("/localize/multi", response_model=MultiFrameLocalizeResponse, dependencies=[Depends(require_scope(SCOPE_QUERY))])
async def localize_multi(
    scene_id: str = Form(...),
    image1: UploadFile | None = File(None),
    image2: UploadFile | None = File(None),
    image3: UploadFile | None = File(None),
    image4: UploadFile | None = File(None),
    image5: UploadFile | None = File(None),
    image6: UploadFile | None = File(None),
    agent_id: str | None = Form(None),
    hint_position: str | None = Form(None),
    hint_radius: float | None = Form(None),
    hint_floor_height: str | None = Form(None),
    geo_hint: str | None = Form(None),
    db: Session = Depends(get_db),
) -> MultiFrameLocalizeResponse:
    imgs = [img for img in [image1, image2, image3, image4] if img]
    if image5:
        imgs.append(image5)
    if image6:
        imgs.append(image6)

    if not imgs:
        raise HTTPException(status_code=422, detail="At least 1 image required")

    saved_paths = []
    for img in imgs:
        path = save_upload(img, f"queries/{scene_id}/multi")
        resize_if_needed(path)
        saved_paths.append(path)

    if len(imgs) < 4:
        logger.info(f"Fewer than 4 images ({len(imgs)}), falling back to single-frame")
        _start_multi = time.time()
        try:
            result = VPSService.localize(
                scene_id=scene_id,
                query_image_path=saved_paths[0],
                db=db,
                hint_position=json.loads(hint_position) if hint_position else None,
                hint_radius=hint_radius or 25.0,
                hint_floor_height=json.loads(hint_floor_height) if hint_floor_height else None,
                geo_hint=json.loads(geo_hint) if geo_hint else None,
            )
            _elapsed = (time.time() - _start_multi) * 1000
            record_query(scene_id, True, _elapsed)
        except ValueError as e:
            _elapsed = (time.time() - _start_multi) * 1000
            record_query(scene_id, False, _elapsed)
            raise HTTPException(status_code=404, detail=str(e)) from e
        except RuntimeError as e:
            _elapsed = (time.time() - _start_multi) * 1000
            record_query(scene_id, False, _elapsed)
            raise HTTPException(status_code=400, detail=str(e)) from e
        except Exception as e:
            _elapsed = (time.time() - _start_multi) * 1000
            record_query(scene_id, False, _elapsed)
            logger.exception("Unexpected error during single-frame fallback")
            raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}") from e
        return MultiFrameLocalizeResponse(
            position=result["position"],
            rotation=result["rotation"],
            inliers=result["inliers"],
            confidence=result["confidence"],
            frames_used=1 if result["inliers"] >= 10 else 0,
            frame_confidences=[result["confidence"]],
            hint_used=result.get("hint_used"),
        )

    _start_multi = time.time()
    try:
        result = VPSService.localize_multi(
            scene_id=scene_id,
            query_image_paths=saved_paths,
            db=db,
            hint_position=json.loads(hint_position) if hint_position else None,
            hint_radius=hint_radius or 25.0,
            hint_floor_height=json.loads(hint_floor_height) if hint_floor_height else None,
            geo_hint=json.loads(geo_hint) if geo_hint else None,
        )
        _elapsed = (time.time() - _start_multi) * 1000
        record_query(scene_id, True, _elapsed)
        logger.info(f"Multi-frame localize result: {result}")

        if agent_id:
            await sync_manager.broadcast(scene_id, {
                "type": "agent_update",
                "agent_id": agent_id,
                "position": result["position"],
                "rotation": result["rotation"]
            })

    except ValueError as e:
        _elapsed = (time.time() - _start_multi) * 1000
        record_query(scene_id, False, _elapsed)
        raise HTTPException(status_code=404, detail=str(e)) from e
    except RuntimeError as e:
        _elapsed = (time.time() - _start_multi) * 1000
        record_query(scene_id, False, _elapsed)
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:
        _elapsed = (time.time() - _start_multi) * 1000
        record_query(scene_id, False, _elapsed)
        logger.exception("Unexpected error during multi-frame localization")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}") from e

    return MultiFrameLocalizeResponse(**result)


@router.websocket("/ws/agents/{scene_id}")
async def agent_sync_websocket(websocket: WebSocket, scene_id: str, api_key: str | None = None):
    """
    WebSocket endpoint for real-time spatial sync.
    """
    from backend.api.auth import validate_ws_api_key
    await validate_ws_api_key(websocket, api_key)
    
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
