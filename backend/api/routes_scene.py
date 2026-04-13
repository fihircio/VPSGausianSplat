from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.api.schemas import SceneProcessResponse, SceneResponse
from backend.models.frame import Frame
from backend.models.scene import Scene
from backend.utils.db import get_db
from backend.utils.storage import ensure_scene_dirs, save_upload
from backend.workers.tasks import process_scene_task

router = APIRouter(prefix="/scene", tags=["scene"])


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
