# VPSGaussianSplat

**Photorealistic Visual Positioning System — Gaussian Splatting–native, web-first, open API.**

Turn a phone video into a 6DoF-localizable AR environment in minutes. No LiDAR, no proprietary SDK lock-in, no mesh pipelines.

[![Status](https://img.shields.io/badge/status-pilot--ready-blueviolet)](https://github.com/fihircio/VPSGausianSplat)
[![Validation](https://img.shields.io/badge/avg_error-4.1cm-success)](docs/validation_checklist.md)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

---

## Why Gaussian Splatting + VPS?

| Problem | Most solutions | This one |
|---------|----------------|----------|
| AR visual quality | Mesh/point-cloud — blocks and dots | **Photorealistic Gaussian splats** — real-time novel view synthesis |
| Platform lock-in | Niantic Lightship, Apple ARKit, Google VPS | **Web-first + Open API** — any device, any framework |
| Pipeline fragmentation | Scan one tool, process another, host a third | **End-to-end unified** — upload → reconstruct → host → localize → deploy |
| Indoor coverage | GPS-denied dead zone | **Private spatial maps** — hospitals, malls, campuses, events |

**Validation:** 0.036m avg translation error, 95% success rate on benchmark (ORB 2000 features, real-world scene).

---

## Quickstart (30 seconds)

```bash
# 1. Upload a video
curl -X POST http://localhost:8000/scene/upload \
  -F "file=@corridor.mp4" \
  -F "name=my-scene"

# → returns {"id": "<scene-id>", ...}

# 2. Process it (COLMAP SfM → FAISS index → Gaussian splat)
curl -X POST http://localhost:8000/scene/<scene-id>/process

# 3. Localize a query frame
curl -X POST http://localhost:8000/vps/localize \
  -F "scene_id=<scene-id>" \
  -F "query_image=@query.jpg"

# → returns {"position": [x,y,z], "rotation": [w,x,y,z], "confidence": 0.89}
```

That's it. From raw video to 6DoF pose in a few minutes.

---

## Architecture

```text
┌─────────────┐    ┌──────────────┐    ┌───────────────┐
│  Frontend    │    │  Navigatus   │    │  Unity SDK    │
│  (Next.js)   │    │  (CRA/PWA)   │    │  (C# package) │
└──────┬───────┘    └──────┬───────┘    └───────┬───────┘
       │                   │                    │
       └───────────────────┼────────────────────┘
                           │ REST API + WebSocket
                           ▼
┌──────────────────────────────────────────────────┐
│              FastAPI Backend  (port 8000)         │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────┐  │
│  │  Scene   │ │  VPS     │ │  Multi-Agent     │  │
│  │  Upload  │ │  Localize│ │  WebSocket Sync  │  │
│  │  Process │ │  FAISS   │ │  Spatial Graph   │  │
│  └────┬─────┘ └────┬─────┘ └────────┬─────────┘  │
│       │            │                │             │
│       ▼            ▼                ▼             │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────┐  │
│  │  COLMAP  │ │  FAISS   │ │  PostgreSQL      │  │
│  │  SfM     │ │  Index   │ │  + Redis         │  │
│  └──────────┘ └──────────┘ └──────────────────┘  │
│  ┌──────────────────────────────────────────────┐ │
│  │  Storage: Local / S3 / Azure Blob            │ │
│  └──────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────┘
```

**Storage backend** is pluggable — swap between local disk, S3, or Azure Blob without code changes.

---

## Modules

| Module | What it does |
|--------|-------------|
| **Capture / Upload** | Video (.mp4, .mov, .webm) or image sequence via REST API. Size limits, format validation, API key gating. |
| **Reconstruction** | COLMAP SfM → sparse point cloud. Gaussian Splatting training (optional, with GPU). FAISS feature index for VPS retrieval. |
| **Viewer** | Web-based Three.js Gaussian splat renderer with octree tiling for large scenes. |
| **VPS Localization** | ORB/SIFT features → FAISS retrieval → PnP RANSAC → 6DoF pose (position, rotation, confidence). |
| **AR Export** | REST anchor API + Unity SDK for deploying to mobile AR apps. |
| **Multi-Agent Sync** | Real-time WebSocket spatial graph for multi-device shared AR experiences. |
| **Synthetic Data** | Google 3D procedural render pipeline for pretraining and evaluation (10K-frame datasets). |

---

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/health` | — | Health check |
| `POST` | `/scene/upload` | API key | Upload video/image for reconstruction |
| `GET` | `/scene` | — | List all scenes |
| `GET` | `/scene/{id}` | — | Scene status and metadata |
| `POST` | `/scene/{id}/process` | API key | Trigger COLMAP SfM + FAISS indexing |
| `DELETE` | `/scene/{id}` | API key | Remove scene data |
| `POST` | `/vps/localize` | API key | Localize a query image against a scene |
| `POST` | `/scene/{id}/anchors` | API key | Create AR anchor |
| `GET` | `/scene/{id}/anchors` | — | List anchors |
| `WS` | `/ws/{scene_id}` | API key | Real-time multi-agent sync |

Full API contract: [`docs/api_contract.md`](docs/api_contract.md)

---

## Quickstart (Full Setup)

### Prerequisites
- Python 3.10+
- PostgreSQL 14+
- Redis 7+
- COLMAP (for SfM reconstruction)
- ffmpeg (for frame extraction)

### Local dev

```bash
git clone https://github.com/fihircio/VPSGausianSplat.git
cd VPSGausianSplat

python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt

cp .env.example .env   # edit DATABASE_URL, API_KEY, etc.
uvicorn backend.api.main:app --reload --port 8000
```

### Using Docker

```bash
docker compose up -d
```

---

## Project Structure

```text
backend/          → FastAPI server + services
  api/            → REST routes, auth, schemas
  services/       → COLMAP, VPS, splatting, features, Google 3D
  workers/        → Celery async tasks
  scripts/        → Benchmarking, synthetic data, evaluation
  models/         → SQLAlchemy ORM models
  utils/          → Config, DB, storage, geometry, ffmpeg
frontend/         → Next.js 16 portal (dashboard, upload, localize, viewer)
navigatus/        → CRA mobile PWA (hospital nav, AR view, scene recording)
docs/             → Commercial, technical, and API documentation
```

---

## Comparison

| | VPSGaussianSplat | MultiSet.ai | Niantic Lightship | Apple ARKit | Immersal |
|---|---|---|---|---|---|
| **Rendering** | Gaussian Splatting (photorealistic) | Mesh | Mesh | Mesh | Mesh |
| **VPS** | Built-in (FAISS + PnP) | Built-in | Built-in | ARWorldMap | Built-in |
| **Platform** | Web + Unity SDK | Mobile SDK | Mobile SDK | iOS only | Mobile SDK |
| **Self-host** | ✅ Open source | ❌ Cloud only | ❌ | ❌ | ❌ |
| **Indoor maps** | ✅ Private scenes | ✅ | ❌ | ❌ | ✅ |
| **Pricing** | Open source + SaaS tiers | Enterprise only | Per query | Free (iOS lock-in) | Per m² |

---

## Documentation

| Link | What |
|------|------|
| [API Contract](docs/api_contract.md) | Full endpoint reference |
| [Capture Protocol](docs/capture_protocol.md) | How to record good scenes |
| [Demo Walkthrough](docs/demo_walkthrough.md) | End-to-end demo script |
| [Validation Check](docs/validation_checklist.md) | Accuracy benchmarks |
| [90-Day Plan](docs/commercialization_90_day_plan.md) | Commercial roadmap |
| [Roadmap Checklist](docs/roadmap_checklist.md) | Current milestone tracking |
| [Google 3D Pipeline](docs/google_3d_training_pipeline.md) | Synthetic data strategy |

---

## License

MIT — see [LICENSE](LICENSE).
