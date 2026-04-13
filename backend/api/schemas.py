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
    error_message: str | None
    frame_count: int = 0
    created_at: datetime
    updated_at: datetime | None = None


class SceneProcessResponse(BaseModel):
    scene_id: str
    task_id: str
    status: str


class LocalizeResponse(BaseModel):
    position: list[float]
    rotation: list[float]  # [qx, qy, qz, qw]
    confidence: float
