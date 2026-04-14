import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile

from backend.utils.config import get_settings


def ensure_scene_dirs(scene_id: str) -> dict[str, Path]:
    settings = get_settings()
    root = settings.storage_root
    raw_dir = root / "raw" / scene_id
    frames_dir = root / "frames" / scene_id
    sparse_dir = root / "recon" / scene_id
    splats_dir = root / "splats" / scene_id
    features_dir = root / "features" / scene_id
    for item in [raw_dir, frames_dir, sparse_dir, splats_dir, features_dir]:
        item.mkdir(parents=True, exist_ok=True)
    return {
        "raw_dir": raw_dir,
        "frames_dir": frames_dir,
        "sparse_dir": sparse_dir,
        "splats_dir": splats_dir,
        "features_dir": features_dir,
    }


def save_upload(upload: UploadFile, target_dir: Path) -> Path:
    target_dir.mkdir(parents=True, exist_ok=True)
    filename = upload.filename or f"upload-{uuid4().hex}"
    out_path = target_dir / filename
    with out_path.open("wb") as f:
        shutil.copyfileobj(upload.file, f)
    return out_path


def purge_scene_data(scene_id: str) -> dict[str, bool]:
    """Deletes temporary reconstruction artifacts while preserving frames and models."""
    dirs = ensure_scene_dirs(scene_id)
    results = {}
    
    # These are the heavy/temporary folders we can safely delete
    to_delete = {
        "raw": dirs["raw_dir"],
        "recon": dirs["sparse_dir"],
        "features": dirs["features_dir"]
    }
    
    for key, path in to_delete.items():
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)
            results[key] = True
        else:
            results[key] = False
            
    return results
