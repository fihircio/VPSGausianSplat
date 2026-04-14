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


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.storage_root.mkdir(parents=True, exist_ok=True)
    return settings
