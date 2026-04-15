import os
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from backend.api.routes_scene import router as scene_router
from backend.api.routes_vps import router as vps_router
from backend.utils.config import get_settings
from backend.utils.db import init_db
from backend.utils.storage import get_storage

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure DB and Storage are ready
    settings = get_settings()
    init_db()
    # Ensure absolute path is used for mounting
    yield

# 1. Initialize Settings
settings = get_settings()
storage_path = str(settings.storage_root.resolve())

app = FastAPI(title="VPS Backend", version="0.1.0", lifespan=lifespan)

# 2. Add Static Mount or Cloud Redirect
if settings.storage_backend.upper() == "LOCAL":
    from fastapi.staticfiles import StaticFiles
    app.mount("/storage", StaticFiles(directory=storage_path), name="storage")
else:
    @app.get("/storage/{file_path:path}")
    async def cloud_storage_proxy(file_path: str):
        storage = get_storage()
        url = storage.get_url(file_path)
        return RedirectResponse(url)

# 3. Add Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 4. Include Routers
app.include_router(scene_router)
app.include_router(vps_router)

@app.get("/health")
def health() -> dict:
    return {"status": "ok"}

@app.get("/debug-path")
def debug_path():
    settings = get_settings()
    root = settings.storage_root.resolve()
    # Check for the specific problematic file
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
