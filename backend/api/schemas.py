from datetime import datetime

from pydantic import BaseModel


class SceneResponse(BaseModel):
    id: str
    name: str
    status: str
    input_type: str
    input_path: str
    frames_dir: str
    sparse_dir: str | None
    splat_path: str | None
    faiss_index_path: str | None
    progress_percent: float = 0.0
    current_task_label: str | None = None
    error_message: str | None
    frame_count: int = 0
    created_at: datetime
    updated_at: datetime | None = None


class FrameResponse(BaseModel):
    id: int
    frame_index: int
    image_path: str
    intrinsics_json: dict | None
    pose_json: dict | None


class SceneFramesResponse(BaseModel):
    scene_id: str
    frames: list[FrameResponse]


class SceneProcessResponse(BaseModel):
    scene_id: str
    task_id: str
    status: str


class LocalizeResponse(BaseModel):
    position: list[float]
    rotation: list[float]  # [qx, qy, qz, qw]
    inliers: int
    confidence: float


class EvaluationSummary(BaseModel):
    scene_id: str
    num_frames: int
    success_rate: float
    avg_inliers: float
    avg_confidence: float
    avg_translation_error: float
    avg_rotation_error: float


class EvaluationResponse(BaseModel):
    summary: EvaluationSummary
    config: dict


# ---------------------------------------------------------------------------
# Anchor schemas
# ---------------------------------------------------------------------------

class AnchorCreate(BaseModel):
    label: str = "Anchor"
    position: list[float]  # [x, y, z]
    rotation: list[float] = [0.0, 0.0, 0.0, 1.0]  # [qx, qy, qz, qw]
    glb_url: str | None = None


class AnchorResponse(BaseModel):
    id: str
    scene_id: str
    label: str
    position: list[float]
    rotation: list[float]
    glb_url: str | None
    created_at: datetime
