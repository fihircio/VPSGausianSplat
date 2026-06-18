import json
from pathlib import Path

from fastapi import APIRouter, HTTPException

from backend.utils.config import get_settings

router = APIRouter(prefix="/settings", tags=["settings"])


def _origins_path() -> Path:
    settings = get_settings()
    return settings.storage_root / "cors_origins.json"


def _load_origins() -> list[str]:
    path = _origins_path()
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text())
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def _save_origins(origins: list[str]):
    _origins_path().write_text(json.dumps(origins, indent=2))


@router.get("/cors-origins")
def get_cors_origins():
    return {"origins": _load_origins()}


@router.post("/cors-origins")
def add_cors_origin(origin: str):
    if not origin or not origin.strip():
        raise HTTPException(status_code=422, detail="Origin must not be empty")
    origin = origin.strip()
    origins = _load_origins()
    if origin in origins:
        raise HTTPException(status_code=409, detail="Origin already in list")
    origins.append(origin)
    _save_origins(origins)
    return {"origins": origins}


@router.delete("/cors-origins/{origin:path}")
def remove_cors_origin(origin: str):
    origins = _load_origins()
    if origin not in origins:
        raise HTTPException(status_code=404, detail="Origin not found in list")
    origins.remove(origin)
    _save_origins(origins)
    return {"origins": origins}
