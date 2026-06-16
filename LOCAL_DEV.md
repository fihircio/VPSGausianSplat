# Local Development Runbook

This runbook starts the VPS backend, admin portal, and Navigatus AR mock locally.

## Ports

| Service | Port |
| --- | --- |
| FastAPI backend | `8000` |
| Admin frontend | `3000` |
| Navigatus | `3001` |
| Redis | `6379` |
| PostgreSQL | `5432` or `5433` |

If local PostgreSQL already uses `5432`, change `backend/docker-compose.yml` to map `5433:5432` and use `localhost:5433` in `DATABASE_URL`.

## 1. Backend Environment

From repo root:

```bash
cp backend/.env.example .env
```

For Docker PostgreSQL on `5433`, set:

```bash
DATABASE_URL=postgresql+psycopg://vps:vps@localhost:5433/vps
```

Install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
```

Start infrastructure:

```bash
cd backend
docker compose up -d
cd ..
```

Start API:

```bash
source .venv/bin/activate
uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload
```

Start worker in a second terminal:

```bash
source .venv/bin/activate
celery -A backend.workers.celery_app:celery_app worker -l info
```

Smoke check:

```bash
scripts/smoke_vps_api.sh
```

With a scene:

```bash
SCENE_ID=<REAL_SCENE_ID> scripts/smoke_vps_api.sh
```

## 2. Admin Frontend

Node requirement:

```bash
node -v
```

The admin frontend uses Next.js 16 and requires Node `>=20.9.0`.

```bash
cd frontend
cp .env.example .env.local
npm install
npm run dev
```

Open:

```bash
http://localhost:3000
```

## 3. Navigatus

Navigatus is the patient-facing AR navigation mock. It consumes `/vps/localize`.

```bash
cd navigatus
cp .env.example .env
```

Set:

```bash
REACT_APP_VPS_API_BASE_URL=http://localhost:8000
REACT_APP_SCENE_ID=<READY_SCENE_ID>
```

Start on port `3001`:

```bash
PORT=3001 npm install
PORT=3001 npm start
```

Open:

```bash
http://localhost:3001
```

## 4. Required Data State

Navigatus localization needs a processed scene:

- `GET /scene/{scene_id}` returns `status: READY`
- `faiss_index_path` is populated
- `feature_meta_path` is populated

If no scene exists, upload and process from the admin portal first.

## 5. Validation Commands

Mapping sanity:

```bash
python -m backend.scripts.validate_feature_mapping --scene-id <READY_SCENE_ID> --frame-index 0
```

Batch localization:

```bash
python -m backend.scripts.test_localization --scene-id <READY_SCENE_ID> --num-frames 20
```

## Current Local Blockers To Watch

- Admin frontend build fails on Node 18. Upgrade to Node `>=20.9.0`.
- Navigatus uses browser camera APIs; use HTTPS or localhost for camera permission.
- VPS output is in COLMAP scene coordinates. Route guidance needs a scene-to-floorplan alignment layer before it is geometrically complete.
