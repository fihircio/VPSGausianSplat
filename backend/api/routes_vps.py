from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.api.schemas import EvaluationResponse, LocalizeResponse
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


@router.get("/evaluation/{scene_id}", response_model=EvaluationResponse)
def get_evaluation(scene_id: str) -> EvaluationResponse:
    import json
    settings = get_settings()
    # Path to the best-config evaluation report
    report_path = settings.storage_root / "debug" / "vps_evaluation_report.json"
    
    if not report_path.exists():
        raise HTTPException(status_code=404, detail="Evaluation report not found")
    
    with open(report_path, "r") as f:
        data = json.load(f)
    
    if data.get("scene_id") != scene_id:
        raise HTTPException(status_code=404, detail=f"No evaluation records for scene {scene_id}")

    best = data.get("best_config", {})
    return EvaluationResponse(
        summary=best.get("summary"),
        config=best.get("config")
    )
