from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.api.schemas import LocalizeResponse
from backend.services.vps import VPSService
from backend.utils.config import get_settings
from backend.utils.db import get_db
from backend.utils.storage import save_upload

router = APIRouter(prefix="/vps", tags=["vps"])


@router.post("/localize", response_model=LocalizeResponse)
def localize(
    scene_id: str = Form(...),
    query_image: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> LocalizeResponse:
    settings = get_settings()
    tmp_dir = settings.storage_root / "queries" / scene_id
    query_path = save_upload(query_image, tmp_dir)
    try:
        result = VPSService.localize(scene_id=scene_id, query_image_path=Path(query_path), db=db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return LocalizeResponse(**result)
