from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.api.schemas import (
    AnchorCreate,
    AnchorResponse,
    FrameResponse,
    SceneFramesResponse,
    SceneProcessResponse,
    SceneResponse,
)
from backend.models.anchor import Anchor
from backend.models.frame import Frame
from backend.models.scene import Scene
from backend.utils.config import get_settings
from backend.utils.db import get_db
from backend.utils.storage import ensure_scene_dirs, save_upload, purge_scene_data
from backend.workers.tasks import process_scene_task
from backend.api.auth import validate_api_key
import threading

router = APIRouter(prefix="/scene", tags=["scene"])


def _to_storage_web_path(path: str | None) -> str | None:
    """Convert local storage paths to FastAPI's /storage URL path.

    Older demo scenes were seeded with absolute filesystem paths. Newer scenes
    store relative paths. API consumers should not need to handle both forms.
    """
    if not path:
        return path
    if path.startswith(("http://", "https://", "/storage/")):
        return path

    settings = get_settings()
    storage_base = settings.storage_root.resolve()

    if path.startswith("/"):
        try:
            rel = Path(path).resolve().relative_to(storage_base)
            return f"/storage/{rel.as_posix()}"
        except ValueError:
            storage_marker = "/backend/storage/"
            if storage_marker in path:
                rel = path.split(storage_marker, 1)[1]
                return f"/storage/{rel.lstrip('/')}"
            return path

    return f"/storage/{path.lstrip('/')}"


def _scene_response(scene: Scene, frame_count: int) -> SceneResponse:
    return SceneResponse(
        id=scene.id,
        name=scene.name,
        status=scene.status,
        input_type=scene.input_type,
        input_path=_to_storage_web_path(scene.input_path) or "",
        frames_dir=_to_storage_web_path(scene.frames_dir) or "",
        sparse_dir=_to_storage_web_path(scene.sparse_dir),
        splat_path=_to_storage_web_path(scene.splat_path),
        faiss_index_path=_to_storage_web_path(scene.faiss_index_path),
        progress_percent=scene.progress_percent,
        current_task_label=scene.current_task_label,
        error_message=scene.error_message,
        frame_count=frame_count,
        created_at=scene.created_at,
        updated_at=scene.updated_at,
    )


@router.get("/", response_model=list[SceneResponse])
def list_scenes(db: Session = Depends(get_db)) -> list[SceneResponse]:
    scenes = db.scalars(select(Scene).order_by(Scene.created_at.desc())).all()
    results = []
    for scene in scenes:
        frame_count = db.scalar(select(func.count(Frame.id)).where(Frame.scene_id == scene.id)) or 0
        results.append(_scene_response(scene, frame_count))
    return results


@router.post("/upload", response_model=SceneResponse, dependencies=[Depends(validate_api_key)])
def upload_scene(
    file: UploadFile = File(...),
    name: str | None = Form(None),
    db: Session = Depends(get_db),
) -> SceneResponse:
    settings = get_settings()

    # Validate file extension
    suffix = Path(file.filename or "").suffix.lower()
    valid_suffixes = {
        ".mp4", ".mov", ".avi", ".mkv", ".webm",  # videos
        ".jpg", ".jpeg", ".png", ".bmp"           # images
    }
    if suffix not in valid_suffixes:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file extension {suffix}. Supported formats: {', '.join(sorted(valid_suffixes))}",
        )

    # Validate content type
    content_type = file.content_type or ""
    is_video = content_type.startswith("video") or suffix in {
        ".mp4", ".mov", ".avi", ".mkv", ".webm"
    }
    is_image = content_type.startswith("image") or suffix in {
        ".jpg", ".jpeg", ".png", ".bmp"
    }
    if not (is_video or is_image):
        raise HTTPException(
            status_code=415,
            detail="Unsupported media type. File must be a valid video or image.",
        )

    # Validate file size
    if file.size is not None:
        max_bytes = settings.max_upload_size_mb * 1024 * 1024
        if file.size > max_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"File is too large ({file.size / 1024 / 1024:.1f} MB). Maximum size allowed is {settings.max_upload_size_mb} MB.",
            )

    scene_id = str(uuid4())
    dirs = ensure_scene_dirs(scene_id)
    input_path = save_upload(file, dirs["raw_dir"])

    input_type = "video" if is_video else "image"

    # Store relative paths in DB
    scene = Scene(
        id=scene_id,
        name=name or f"scene-{scene_id[:8]}",
        status="UPLOADED",
        input_type=input_type,
        input_path=f"raw/{scene_id}/{Path(input_path).name}",
        frames_dir=f"frames/{scene_id}",
        sparse_dir=f"recon/{scene_id}",
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
        progress_percent=scene.progress_percent,
        current_task_label=scene.current_task_label,
        error_message=scene.error_message,
        frame_count=0,
        created_at=scene.created_at,
        updated_at=scene.updated_at,
    )


@router.post("/{scene_id}/process", response_model=SceneProcessResponse, dependencies=[Depends(validate_api_key)])
def process_scene(scene_id: str, force_rebuild: bool = False, db: Session = Depends(get_db)) -> SceneProcessResponse:
    scene = db.get(Scene, scene_id)
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")
    scene.status = "QUEUED"
    scene.error_message = None
    db.add(scene)
    db.commit()
    task_id = str(uuid4())
    threading.Thread(target=process_scene_task, args=(scene_id, force_rebuild), daemon=True).start()
    return SceneProcessResponse(scene_id=scene_id, task_id=task_id, status="QUEUED")


@router.get("/{scene_id}", response_model=SceneResponse)
def get_scene(scene_id: str, db: Session = Depends(get_db)) -> SceneResponse:
    scene = db.get(Scene, scene_id)
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")
    frame_count = db.scalar(select(func.count(Frame.id)).where(Frame.scene_id == scene_id)) or 0
    return _scene_response(scene, frame_count)


@router.get("/{scene_id}/frames", response_model=SceneFramesResponse)
def get_scene_frames(scene_id: str, db: Session = Depends(get_db)) -> SceneFramesResponse:
    # Limit to 300 frames to ensure viewer performance
    frames = db.scalars(
        select(Frame)
        .where(Frame.scene_id == scene_id)
        .order_by(Frame.frame_index.asc())
        .limit(300)
    ).all()

    return SceneFramesResponse(
        scene_id=scene_id,
        frames=[
            FrameResponse(
                id=f.id,
                frame_index=f.frame_index,
                image_path=_to_storage_web_path(f.image_path) or "",
                intrinsics_json=f.intrinsics_json,
                pose_json=f.pose_json,
            )
            for f in frames
        ],
    )


@router.delete("/{scene_id}/cleanup", dependencies=[Depends(validate_api_key)])
def cleanup_scene_storage(scene_id: str, db: Session = Depends(get_db)):
    settings = get_settings()
    if not settings.allow_destructive_endpoints:
        raise HTTPException(status_code=403, detail="Destructive endpoints are disabled.")
    scene = db.get(Scene, scene_id)
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")
    
    results = purge_scene_data(scene_id)
    return {
        "scene_id": scene_id,
        "purged": results,
        "message": "Heavy raw data and reconstruction artifacts successfully removed."
    }


# ---------------------------------------------------------------------------
# Tile Manifest endpoint
# ---------------------------------------------------------------------------

@router.get("/{scene_id}/tiles/manifest")
def get_tile_manifest(scene_id: str, db: Session = Depends(get_db)):
    """
    Return the octree tile manifest JSON for the scene.
    The manifest is written by backend/scripts/tile_splat.py prior to calling this.
    """
    settings = get_settings()
    manifest_path = (
        settings.storage_root / "splats" / scene_id / "tiles" / "tile_manifest.json"
    )
    if not manifest_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Tile manifest not found. Run tile_splat.py for this scene first.",
        )
    import json
    return json.loads(manifest_path.read_text())


# ---------------------------------------------------------------------------
# Anchor CRUD endpoints
# ---------------------------------------------------------------------------

@router.get("/{scene_id}/anchors", response_model=list[AnchorResponse])
def list_anchors(scene_id: str, db: Session = Depends(get_db)) -> list[AnchorResponse]:
    """List all anchors for a scene."""
    scene = db.get(Scene, scene_id)
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")
    anchors = db.scalars(
        select(Anchor).where(Anchor.scene_id == scene_id).order_by(Anchor.created_at.asc())
    ).all()
    return [
        AnchorResponse(
            id=a.id,
            scene_id=a.scene_id,
            label=a.label,
            position=[a.position_x, a.position_y, a.position_z],
            rotation=[a.rotation_x, a.rotation_y, a.rotation_z, a.rotation_w],
            glb_url=a.glb_url,
            created_at=a.created_at,
        )
        for a in anchors
    ]


@router.post("/{scene_id}/anchors", response_model=AnchorResponse, status_code=201)
def create_anchor(
    scene_id: str, body: AnchorCreate, db: Session = Depends(get_db)
) -> AnchorResponse:
    """Persist a new 3D anchor for a scene."""
    scene = db.get(Scene, scene_id)
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")
    if len(body.position) != 3:
        raise HTTPException(status_code=422, detail="position must be [x, y, z]")
    rot = body.rotation if len(body.rotation) == 4 else [0.0, 0.0, 0.0, 1.0]

    anchor = Anchor(
        scene_id=scene_id,
        label=body.label,
        position_x=body.position[0],
        position_y=body.position[1],
        position_z=body.position[2],
        rotation_x=rot[0],
        rotation_y=rot[1],
        rotation_z=rot[2],
        rotation_w=rot[3],
        glb_url=body.glb_url,
    )
    db.add(anchor)
    db.commit()
    db.refresh(anchor)
    return AnchorResponse(
        id=anchor.id,
        scene_id=anchor.scene_id,
        label=anchor.label,
        position=[anchor.position_x, anchor.position_y, anchor.position_z],
        rotation=[anchor.rotation_x, anchor.rotation_y, anchor.rotation_z, anchor.rotation_w],
        glb_url=anchor.glb_url,
        created_at=anchor.created_at,
    )


@router.delete("/{scene_id}/anchors/{anchor_id}", status_code=204, dependencies=[Depends(validate_api_key)])
def delete_anchor(
    scene_id: str, anchor_id: str, db: Session = Depends(get_db)
) -> None:
    settings = get_settings()
    if not settings.allow_destructive_endpoints:
        raise HTTPException(status_code=403, detail="Destructive endpoints are disabled.")
    """Remove an anchor by ID."""
    anchor = db.get(Anchor, anchor_id)
    if not anchor or anchor.scene_id != scene_id:
        raise HTTPException(status_code=404, detail="Anchor not found")
    db.delete(anchor)
    db.commit()
