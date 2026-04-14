from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.api.schemas import (
    FrameResponse,
    SceneFramesResponse,
    SceneProcessResponse,
    SceneResponse,
)
from backend.models.frame import Frame
from backend.models.scene import Scene
from backend.utils.config import get_settings
from backend.utils.db import get_db
from backend.utils.storage import ensure_scene_dirs, save_upload, purge_scene_data
from backend.workers.tasks import process_scene_task

router = APIRouter(prefix="/scene", tags=["scene"])


@router.get("/", response_model=list[SceneResponse])
def list_scenes(db: Session = Depends(get_db)) -> list[SceneResponse]:
    scenes = db.scalars(select(Scene).order_by(Scene.created_at.desc())).all()
    results = []
    for scene in scenes:
        frame_count = db.scalar(select(func.count(Frame.id)).where(Frame.scene_id == scene.id)) or 0
        results.append(
            SceneResponse(
                id=scene.id,
                name=scene.name,
                status=scene.status,
                input_type=scene.input_type,
                input_path=scene.input_path,
                frames_dir=scene.frames_dir,
                sparse_dir=scene.sparse_dir,
                splat_path=scene.splat_path,
                faiss_index_path=scene.faiss_index_path,
                error_message=scene.error_message,
                frame_count=frame_count,
                created_at=scene.created_at,
                updated_at=scene.updated_at,
            )
        )
    return results


@router.post("/upload", response_model=SceneResponse)
def upload_scene(
    file: UploadFile = File(...),
    name: str | None = Form(None),
    db: Session = Depends(get_db),
) -> SceneResponse:
    scene_id = str(uuid4())
    dirs = ensure_scene_dirs(scene_id)
    input_path = save_upload(file, dirs["raw_dir"])

    suffix = Path(file.filename or "").suffix.lower()
    is_video = (file.content_type or "").startswith("video") or suffix in {
        ".mp4",
        ".mov",
        ".avi",
        ".mkv",
        ".webm",
    }
    input_type = "video" if is_video else "image"

    scene = Scene(
        id=scene_id,
        name=name or f"scene-{scene_id[:8]}",
        status="UPLOADED",
        input_type=input_type,
        input_path=str(input_path.resolve()),
        frames_dir=str(dirs["frames_dir"].resolve()),
        sparse_dir=str(dirs["sparse_dir"].resolve()),
        splat_path=None,
        faiss_index_path=None,
    )
    db.add(scene)
    db.commit()
    db.refresh(scene)

    return SceneResponse(
        id=scene.id,
        name=scene.name,
        status=scene.status,
        input_type=scene.input_type,
        input_path=scene.input_path,
        frames_dir=scene.frames_dir,
        sparse_dir=scene.sparse_dir,
        splat_path=scene.splat_path,
        faiss_index_path=scene.faiss_index_path,
        error_message=scene.error_message,
        frame_count=0,
        created_at=scene.created_at,
        updated_at=scene.updated_at,
    )


@router.post("/{scene_id}/process", response_model=SceneProcessResponse)
def process_scene(scene_id: str, force_rebuild: bool = False, db: Session = Depends(get_db)) -> SceneProcessResponse:
    scene = db.get(Scene, scene_id)
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")
    task = process_scene_task.delay(scene_id, force_rebuild)
    scene.status = "QUEUED"
    scene.error_message = None
    db.add(scene)
    db.commit()
    return SceneProcessResponse(scene_id=scene_id, task_id=task.id, status="QUEUED")


@router.get("/{scene_id}", response_model=SceneResponse)
def get_scene(scene_id: str, db: Session = Depends(get_db)) -> SceneResponse:
    scene = db.get(Scene, scene_id)
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")
    frame_count = db.scalar(select(func.count(Frame.id)).where(Frame.scene_id == scene_id)) or 0
    return SceneResponse(
        id=scene.id,
        name=scene.name,
        status=scene.status,
        input_type=scene.input_type,
        input_path=scene.input_path,
        frames_dir=scene.frames_dir,
        sparse_dir=scene.sparse_dir,
        splat_path=scene.splat_path,
        faiss_index_path=scene.faiss_index_path,
        error_message=scene.error_message,
        frame_count=frame_count,
        created_at=scene.created_at,
        updated_at=scene.updated_at,
    )


@router.get("/{scene_id}/frames", response_model=SceneFramesResponse)
def get_scene_frames(scene_id: str, db: Session = Depends(get_db)) -> SceneFramesResponse:
    settings = get_settings()
    # Limit to 300 frames to ensure viewer performance
    frames = db.scalars(
        select(Frame)
        .where(Frame.scene_id == scene_id)
        .order_by(Frame.frame_index.asc())
        .limit(300)
    ).all()

    # Helper to convert absolute path to web-accessible URL
    storage_base = settings.storage_root.resolve()

    def to_web_path(abs_path: str) -> str:
        try:
            # Strip the absolute storage root and prepend /storage mount point
            abs_p = Path(abs_path).resolve()
            rel = abs_p.relative_to(storage_base)
            return f"/storage/{rel}"
        except (ValueError, AttributeError):
            # Fallback if path logic fails
            return abs_path

    return SceneFramesResponse(
        scene_id=scene_id,
        frames=[
            FrameResponse(
                id=f.id,
                frame_index=f.frame_index,
                image_path=to_web_path(f.image_path),
                intrinsics_json=f.intrinsics_json,
                pose_json=f.pose_json,
            )
            for f in frames
        ],
    )


@router.delete("/{scene_id}/cleanup")
def cleanup_scene_storage(scene_id: str, db: Session = Depends(get_db)):
    scene = db.get(Scene, scene_id)
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")
    
    results = purge_scene_data(scene_id)
    return {
        "scene_id": scene_id,
        "purged": results,
        "message": "Heavy raw data and reconstruction artifacts successfully removed."
    }
