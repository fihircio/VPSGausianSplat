from celery import Celery

from backend.utils.config import get_settings

settings = get_settings()

celery_app = Celery(
    "vps_backend",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["backend.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
)
