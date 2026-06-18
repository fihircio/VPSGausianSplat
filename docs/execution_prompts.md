# Execution Prompts — Status & Remaining Work

Last updated: 2026-06-19

## Status Summary

| Prompt | Task | Status | Commit |
|---|---|---|---|
| PROMPT 1 | Spatial Hints | ✅ Completed | `184f608` |
| PROMPT 2 | Multi-Frame VPS | ✅ Completed | `c664876`, `32b1807` |
| PROMPT 3 | Image Resize + JWT Auth | ✅ Completed | `184f608` |
| PROMPT 4 | Navigatus Resize + Race Fix + Polish | ✅ Completed | `184f608`, `978b624`, `c664876` |
| PROMPT 5 | Frontend Multi-Frame UI | ✅ Completed | `c664876` |
| PROMPT 6 | CORS UI + Analytics Dashboard | ✅ Completed | `4b76585`, `32b1807` |
| PROMPT 7 | WebXR NPM Package (`@vps/web-client`) | ✅ Completed | `5372ee8` |
| PROMPT 8 (was 9) | Unity SDK Expansion | ✅ Completed | `813897d` |
| PROMPT 9 | Reprocess Psychiatry Wing | ⏳ **Deferred** (needs original video) | — |
| PROMPT 10 | Google 3D Pipeline Validation | ⏳ **In progress** (Blender 5.0.1 installed, `blender_bin` configured) | `7d24990` |
| PROMPT 11 | End-to-End Validation | ⏳ **Deferred** | — |
| PROMPT 12 | Field Capture at Synthetic AOI | ⏳ **Deferred** | — |

---

## ✅ PROMPT 1: Spatial Hints — COMPLETED

**Status:** Done in `184f608`
**Files modified:** `backend/api/routes_vps.py`, `backend/services/vps.py`, `backend/api/schemas.py`
**API:** `POST /vps/localize` accepts `hint_position`, `hint_radius`, `hint_floor_height`, `geo_hint`
**Result:** 61 inliers with `hint_position` vs 20 without on Psikiatrik 1
**Frontend:** `hint_used` field in `LocalizeResponse`

hint_position, hint_radius, hint_floor_height, geo_hint all implemented and working.

---

## ✅ PROMPT 2: Multi-Frame VPS — COMPLETED

**Status:** Done in `c664876` (backend + frontend + navigatus), `32b1807` (wire-up fixes)
**Files modified:** `backend/api/routes_vps.py`, `backend/services/vps.py`, `backend/api/schemas.py`, `frontend/lib/api.ts`, `frontend/types/index.ts`, `navigatus/src/lib/vpsClient.ts`, `frontend/app/localize/page.tsx`
**API:** `POST /vps/localize/multi` accepts 4-6 images, merges correspondences, single PnP solve
**Result:** 71 inliers with 4 frames vs 20 single-frame on Psikiatrik 1
**Fallback:** < 4 images → call `VPSService.localize()` on first image and wrap into `MultiFrameLocalizeResponse`

`POST /vps/localize/multi` accepts 4-6 images, merges correspondences, single PnP solve. Navigatus has `localizeMultiVideoFrame()`.

---

## ✅ PROMPT 3: Image Resize + JWT Auth — COMPLETED

**Status:** Done in `184f608`
**Files modified:** `backend/utils/image.py`, `backend/api/auth.py`, `backend/api/routes_vps.py`, `backend/utils/config.py`, `backend/models/tenant.py`, `backend/models/api_key.py`, `navigatus/src/lib/vpsClient.ts`
**Image resize:** `resize_if_needed()` caps images at 1280px max dimension (server-side)
**JWT auth:** `validate_auth()` backward-compat with `X-API-Key` + JWT Bearer. `require_scope()` granular access control.
**Auth endpoints:** `POST /auth/token`, `POST /auth/register`

1280px resize on both server and client. JWT multi-tenant with `require_scope()` replacing `validate_api_key` on VPS routes.

---

## ✅ PROMPT 4: Navigatus Resize + Race Fix + Polish — COMPLETED

**Status:** Done in `184f608` (resize), `978b624` (race fix + multi-frame warmup), `c664876` (multi-frame in vpsClient.ts)
**Files modified:** `navigatus/src/lib/vpsClient.ts`, `navigatus/src/App.tsx`
**Capture:** Capped at 1280px via `captureVideoFrame(video, maxDimension=1280)`
**Race fix:** `isLocalizingRef` prevents concurrent localizations
**Multi-frame:** `localizeMultiVideoFrame()` captures 4 frames at 500ms intervals, posts to `/vps/localize/multi`

---

## ✅ PROMPT 5: Frontend Multi-Frame UI — COMPLETED

**Status:** Done in `c664876`
**Files modified:** `frontend/app/localize/page.tsx` (major rewrite), `frontend/lib/api.ts`, `frontend/types/index.ts`
**UI features:**
- Single Frame / Multi Frame tab toggle
- Webcam capture: 4 frames at 500ms intervals with preview thumbnails
- Per-frame confidence display
- Result card showing inliers, frames used, position/rotation

---

## ✅ PROMPT 6: CORS UI + Analytics Dashboard — COMPLETED

**Status:** Done in `4b76585`, `32b1807` (file-based CORS sync)
**Files modified:**
- `backend/api/main.py` — CORS middleware configurable via API
- `backend/api/routes_settings.py` — `GET/POST/DELETE /settings/cors-origins`
- `backend/api/routes_analytics.py` — `GET /analytics/overview`, `/analytics/daily`
- `backend/utils/metrics.py` — Redis-based query metric tracking (p50/p95/p99 latency, success rate)
- `frontend/app/settings/page.tsx` — CORS origins management UI
- `frontend/app/analytics/page.tsx` — Analytics dashboard with daily query chart
- `frontend/components/Navbar.tsx` — Links to Settings + Analytics
- `frontend/lib/api.ts` — CORS + analytics API client methods

---

## ✅ PROMPT 7: WebXR NPM Package (`@vps/web-client`) — COMPLETED

**Status:** Done in `5372ee8`
**Files:** `packages/vps-webxr/`
**Directory structure:**
```
packages/vps-webxr/
├── package.json          # @vps/web-client v0.1.0
├── tsconfig.json
├── src/
│   ├── index.ts          # exports VpsClient, connectVpsWebSocket, types
│   ├── VpsClient.ts      # main class
│   ├── types.ts          # API interfaces
│   └── websocket.ts      # multi-agent WebSocket sync
└── dist/                 # built JS + .d.ts (committed for local-path installs)
```

**VpsClient API:**
- `new VpsClient(baseUrl, apiKey?)` — constructor
- `localize(sceneId, image: Blob, options?)` → `LocalizeResponse`
- `localizeMulti(sceneId, images: Blob[], options?)` → `MultiFrameLocalizeResponse`
- `getScene(sceneId)` → `Scene`
- `listScenes()` → `Scene[]`
- `connectVpsWebSocket(url, sceneId, agentId, onUpdate, onError?)` → `WebSocket`

**All spatial hints supported:** `hintPosition`, `hintRadius`, `hintFloorHeight`, `geoHint`
**Verified:** `npm install /path/to/packages/vps-webxr` works — `new VpsClient('http://localhost:8002')` instantiates correctly.

### Acceptance Criteria
- [x] `npm install /path/to/packages/vps-webxr` works
- [x] `const client = new VpsClient(url, key); await client.localize(sceneId, blob)` returns pose
- [x] TypeScript types exported properly
- [x] WebSocket sync helper created
- [x] Installable from local path

---

---

## ✅ PROMPT 8 (was 9): Unity SDK Expansion — COMPLETED

**Status:** Done in `813897d`
**Files modified:** 10 files, +1024/-33 lines

### Unity SDK Structure
```
unity-sdk/com.vps.sdk/
├── Runtime/Scripts/
│   ├── VPSDataModels.cs          # MultiFrameLocalizationResponse, SpatialHintOptions
│   ├── VPSClient.cs               # Localize (with hints), LocalizeMulti, CancelActiveRequest
│   ├── MapSpace.cs                # Multi-frame responses, RequestMultiFrameLocalization
│   └── WebSocketClient.cs         # Multi-agent WebSocket pose sync
└── Samples~/
    ├── Localization/
    │   ├── LocalizationController.cs  # Single-frame AR with WebCamTexture
    │   └── README.md
    ├── Navigation/
    │   ├── NavigationController.cs    # NavMesh agent driven by VPS pose
    │   └── README.md
    └── MultiFrame/
        ├── MultiFrameController.cs    # 4-frame capture with confidence bars
        └── README.md
```

### Acceptance Criteria
- [x] LocalizationSample — AR WebCamTexture + VPS localize + pose alignment
- [x] NavigationSample — NavMeshAgent driven by VPS pose + target selection
- [x] MultiFrameSample — 4-frame capture, per-frame confidence, combined pose
- [x] VPSClient.cs — hint params + multi-frame wrapper + cancel support
- [x] Coordinate conversion — LHS (Unity) ↔ RHS (COLMAP/OpenCV)
- [x] WebSocketClient.cs — multi-agent pose sync

---

## ⏳ PROMPT 9: Reprocess Psychiatry Wing — DEFERRED

**Scene ID:** `299a4c07-c927-431c-b397-123d959f4e7b` (was FAILED)
**Status:** ⏳ **Deferred** — original video file lost during repo corruption. Need to either re-capture or find a backup.

**What remains:**
- WIP/ directory has two backend storage dirs: `WIP/backend/storage/` (old) and `WIP/VPSGausianSplat/backend/storage/` (git repo)
- Old `backend/storage/features/57528008-*` has Psikiatrik 1 feature data (from initial setup)
- Current database (`vps.db`) is empty — all scenes need re-upload
- Psychiatry Wing video (`.mp4`) must be re-captured or restored from backup

### Troubleshooting (when video is available)
1. Lower COLMAP `min_inlier_ratio` or `max_error` in reconstruction parameters
2. Reduce `MIN_INLIERS` in `VPSService` (currently 20) to accept weaker localizations
3. Switch `FEATURE_MODE` to SUPERPOINT (requires torch, blocked by page file)
4. Check video: verify sufficient camera movement (min 30cm baseline)
5. Re-extract frames at higher FPS (`DEFAULT_VIDEO_FPS=4` instead of 2)

---

## ⏳ PROMPT 10: Google 3D Pipeline Validation — DEFERRED

**Status:** Infrastructure ready, Google Maps API key needed

### What's set up
| Component | Status | Details |
|---|---|---|
| Blender 5.0.1 | ✅ Installed | `C:\Program Files\Blender Foundation\Blender 5.0\blender.exe` |
| `blender_bin` config | ✅ Done | `backend/utils/config.py:28` + `backend/.env` |
| Blender headless `-P` | ✅ Verified | Script works, `bpy` imports correctly |
| AOI registry | ✅ Ready | `klcc_001`, `bukit_bintang_001`, `merdeka_square_001` |
| Google Maps API key | ❌ Missing | Must set `GOOGLE_API_KEY` in `.env` to use tile downloader |

### Pipeline steps
1. **Ingest AOI manifest** — `python -m backend.scripts.google3d_ingest_aoi` (works offline)
2. **Download tiles** — `TileDownloader.fetch_aoi_tiles()` (requires API key)
3. **Build scene** — `scene_builder.py` merges GLB meshes
4. **Render frames** — `run_blender()` via `mesh_renderer.py`
5. **Feature benchmark** — `google3d_eval_features --modes ORB SIFT`

### Key files
- `backend/services/google3d/mesh_renderer.py` — Blender headless renderer
- `backend/services/google3d/scene_builder.py` — GLB mesh assembler
- `backend/services/google3d/tile_downloader.py` — Google 3D Tiles API
- `backend/services/google3d/camera_paths.py` — Synthetic trajectory generator
- `backend/services/google3d/rendering.py` — Procedural (OpenCV) fallback
- `docs/google_3d_training_pipeline.md` — Full architecture
- `docs/google_3d_agent_handoff.md` — Agent task breakdown

---

## ⏳ DEFERRED — PROMPT 11: End-to-End Validation

**Goal:** Validate all Phase 1 features end-to-end.
**Status:** Deferred until Psychiatry Wing + Google 3D pipeline are stable.

### Test Matrix (10 tests)
| T# | Test | Expected |
|----|------|----------|
| T1 | Upload video → process → READY | `scene.status == "READY"` |
| T2 | Single-frame localize | Inliers ≥ 20 |
| T3 | Spatial hint: hintPosition | Faster, fewer matches |
| T4 | Spatial hint: hintFloorHeight | Filters to Y-band |
| T5 | Spatial hint: geoHint | Graceful skip |
| T6 | Multi-frame 4 images | `frames_used ≥ 2` |
| T7 | JWT valid token | 200 OK |
| T8 | JWT invalid token | 401 |
| T9 | JWT missing scope | 403 |
| T10 | Image resize: 4K input | Resized ≤1280px |

---

## ⏳ DEFERRED — PROMPT 12: Field Capture at Synthetic AOI

**Goal:** Real-world video at KL target AOIs to validate synthetic-to-real transfer.
**Prerequisites:** Google 3D pipeline validated, stable reconstruction.

### Target Locations
1. **KLCC** — Suria KLCC, KLCC Park
2. **Bukit Bintang** — Pavilion, Starhill intersection
3. **Merdeka Square** — Dataran Merdeka

### What to Validate
1. Does synthetic data transfer to real-world?
2. How many frames for reliable localization?
3. Accuracy vs ground truth (GPS + visual)
4. Multi-frame improvement over single-frame
5. Spatial hints in large open areas (KLCC)
