from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.api.schemas import EvaluationResponse, LocalizeResponse
from backend.services.vps import VPSService
from backend.utils.config import get_settings
from backend.utils.db import get_db
from backend.utils.storage import save_upload, get_storage

router = APIRouter(prefix="/vps", tags=["vps"])


@router.post("/localize", response_model=LocalizeResponse)
def localize(
    scene_id: str = Form(...),
    query_image: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> LocalizeResponse:
    settings = get_settings()
    query_path = save_upload(query_image, f"queries/{scene_id}")
    try:
        result = VPSService.localize(scene_id=scene_id, query_image_path=query_path, db=db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    return LocalizeResponse(**result)


@router.get("/evaluation/{scene_id}", response_model=EvaluationResponse)
def get_evaluation(scene_id: str) -> EvaluationResponse:
    import json
    settings = get_settings()
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
