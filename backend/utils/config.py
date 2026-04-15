from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
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


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.storage_root.mkdir(parents=True, exist_ok=True)
    return settings
