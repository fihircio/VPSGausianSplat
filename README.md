# VPS + Gaussian Splatting MVP Backend

This repository contains an MVP backend for a Visual Positioning System (VPS) pipeline integrated with COLMAP reconstruction and Gaussian Splatting-compatible output.

## Stack

- Python 3.10+
- FastAPI
- Celery + Redis
- PostgreSQL
- OpenCV ORB
- FAISS
- COLMAP (external binary)
- ffmpeg (external binary)
- PyTorch (for future/optional Gaussian Splatting training execution)

## Project Structure

```text
backend/
  api/
    main.py
    routes_scene.py
    routes_vps.py
    schemas.py
  services/
    reconstruction.py
    splatting.py
    vps.py
  workers/
    celery_app.py
    tasks.py
  models/
    base.py
    scene.py
    frame.py
    feature_set.py
  utils/
    config.py
    db.py
    ffmpeg.py
    geometry.py
    storage.py
  storage/
    raw/
    frames/
    recon/
    splats/
    features/
```

## What the MVP Implements

1. Input upload (`image` or `video`)
2. Frame extraction via ffmpeg
3. COLMAP SfM pipeline (`feature_extractor`, `exhaustive_matcher`, `mapper`, `model_converter`)
4. Camera intrinsics/extrinsics parsed and stored per frame
5. Gaussian Splatting integration path:
   - If `GAUSSIAN_SPLATTING_REPO` is configured and valid, backend calls graphdeco `train.py`
   - Otherwise, fallback `.ply` is exported from COLMAP sparse points
6. ORB feature database for VPS:
   - ORB features extracted on reconstructed frames
   - Adjacent-frame triangulation builds 3D landmarks
   - FAISS index stores descriptors
7. VPS localization API:
   - Query image ORB features
   - FAISS retrieval for landmark matches
   - `solvePnPRansac` pose estimation
   - Returns `{position, rotation, confidence}`

## API Endpoints

- `POST /scene/upload`
- `POST /scene/{id}/process`
- `GET /scene/{id}`
- `POST /vps/localize`
- `GET /health`

## Local Run Instructions

### 1) Infrastructure

```bash
cd /Users/fihiromar/Desktop/WORKS/20260308_VPSMAP/WIP/backend
docker compose up -d
```

### 2) Python env

```bash
cd /Users/fihiromar/Desktop/WORKS/20260308_VPSMAP/WIP
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
cp backend/.env.example .env
```

Set these in `.env` if needed:
- `COLMAP_BIN` (default `colmap`)
- `FFMPEG_BIN` (default `ffmpeg`)
- `GAUSSIAN_SPLATTING_REPO` (optional path to graphdeco repo)

### 3) Run API

```bash
uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4) Run worker

```bash
celery -A backend.workers.celery_app:celery_app worker -l info
```

## Example API Usage

### Upload a scene

```bash
curl -X POST http://localhost:8000/scene/upload \
  -F "name=test-scene" \
  -F "file=@/absolute/path/to/video.mp4"
```

### Process scene

```bash
curl -X POST http://localhost:8000/scene/<scene_id>/process
```

### Query scene status

```bash
curl http://localhost:8000/scene/<scene_id>
```

### Localize query image

```bash
curl -X POST http://localhost:8000/vps/localize \
  -F "scene_id=<scene_id>" \
  -F "query_image=@/absolute/path/to/query.jpg"
```

Expected localization response:

```json
{
  "position": [1.23, -0.51, 2.07],
  "rotation": [0.01, 0.72, -0.03, 0.69],
  "confidence": 0.78
}
```

## Notes

- This is an MVP pipeline prioritizing modularity and end-to-end flow.
- ORB is used intentionally for baseline simplicity.
- Database schema is created automatically at app startup.
- For production, add migrations (Alembic), object storage abstraction (S3 client), and robust monitoring/logging.
