from fastapi import FastAPI

from fastapi.middleware.cors import CORSMiddleware
from backend.api.routes_scene import router as scene_router
from backend.api.routes_vps import router as vps_router
from backend.utils.config import get_settings
from backend.utils.db import init_db

settings = get_settings()

app = FastAPI(title=settings.app_name, version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(scene_router)
app.include_router(vps_router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.on_event("startup")
def on_startup() -> None:
    init_db()
