import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from backend.api.routes_auth import router as auth_router
from backend.api.routes_scene import router as scene_router
from backend.api.routes_vps import router as vps_router
from backend.api.routes_settings import router as settings_router
from backend.api.routes_analytics import router as analytics_router
from backend.utils.config import get_settings
from backend.utils.db import init_db, SessionLocal
from backend.utils.storage import get_storage
from backend.services.sync_service import sync_manager

async def persist_agent_states_loop():
    while True:
        try:
            await asyncio.sleep(5)
            with SessionLocal() as db:
                sync_manager.persist_agent_states(db)
        except Exception as e:
            import logging
            logging.getLogger("backend.api.main").error(f"Persistence loop error: {e}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    init_db()
    persistence_task = asyncio.create_task(persist_agent_states_loop())
    yield
    persistence_task.cancel()
    try:
        await persistence_task
    except asyncio.CancelledError:
        pass

settings = get_settings()
storage_path = str(settings.storage_root.resolve())

app = FastAPI(title="VPS Backend", version="0.1.0", lifespan=lifespan)

if settings.storage_backend.upper() == "LOCAL":
    from fastapi.staticfiles import StaticFiles
    app.mount("/storage", StaticFiles(directory=storage_path), name="storage")
else:
    @app.get("/storage/{file_path:path}")
    async def cloud_storage_proxy(file_path: str):
        storage = get_storage()
        url = storage.get_url(file_path)
        return RedirectResponse(url)

cors_origins_env = settings.cors_allowed_origins
if cors_origins_env == "*":
    cors_origins_list = ["*"]
else:
    cors_origins_list = [o.strip() for o in cors_origins_env.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(scene_router)
app.include_router(vps_router)
app.include_router(settings_router)
app.include_router(analytics_router)

@app.get("/health")
def health() -> dict:
    return {"status": "ok"}

@app.get("/debug-path")
def debug_path():
    from fastapi import HTTPException
    import os
    settings = get_settings()
    if not settings.allow_debug_endpoints:
        raise HTTPException(status_code=403, detail="Debug endpoints are disabled.")
    root = settings.storage_root.resolve()
    target_ply = root / "splats" / "bcaa4187-b6f0-4d4c-8996-b234ba0af8e1" / "sparse_points_fallback.ply"
    return {
        "storage_root": str(root),
        "root_exists": root.exists(),
        "target_file": str(target_ply),
        "file_exists_on_disk": target_ply.exists(),
        "cwd": os.getcwd(),
    }
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.api.main:app", host="0.0.0.0", port=8000, reload=True)
