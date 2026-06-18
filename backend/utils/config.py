from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


_backend_env = str(Path(__file__).resolve().parent.parent / ".env")

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(_backend_env, ".env"),
        extra="ignore"
    )

    app_name: str = "VPS Gaussian Splatting Backend"
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    database_url: str = "postgresql+psycopg://vps:vps@localhost:5432/vps"
    redis_url: str = "redis://localhost:6379/0"

    storage_root: Path = Field(
        default_factory=lambda: Path(__file__).resolve().parent.parent.parent / "backend" / "storage"
    )
    ffmpeg_bin: str = "ffmpeg"
    colmap_bin: str = "colmap"
    blender_bin: str = "blender"
    gaussian_splatting_repo: str = ""
    default_video_fps: int = 2
    orb_nfeatures: int = 3000
    feature_mode: str = "ORB"  # ORB or SUPERPOINT
    sp_max_keypoints: int = 2048
    sp_conf_threshold: float = 0.001

    # Storage Settings
    storage_backend: str = "LOCAL"  # LOCAL, S3, or AZURE
    s3_bucket: str = ""
    s3_region: str = "us-east-1"
    s3_access_key: str = ""
    s3_secret_key: str = ""
    azure_connection_string: str = ""
    azure_container: str = "vps-storage"

    # Security & Gating Settings
    api_key: str | None = None
    google_api_key: str = ""
    allow_debug_endpoints: bool = True
    allow_destructive_endpoints: bool = True
    max_upload_size_mb: int = 500

    # CORS Settings
    cors_allowed_origins: str = "*"  # comma-separated or "*" for all

    # JWT Settings
    jwt_secret: str = "change-me-in-production-use-a-long-random-string"
    jwt_algorithm: str = "HS256"
    jwt_expiry_hours: int = 24
    admin_api_key: str | None = None


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.storage_root.mkdir(parents=True, exist_ok=True)
    return settings
