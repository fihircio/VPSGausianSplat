# Execution Prompts — Status & Remaining Work

Last updated: 2026-06-19

## Status Summary

| Prompt | Task | Status |
|---|---|---|
| PROMPT 1 | Spatial Hints | ✅ Completed (`184f608`) |
| PROMPT 2 | Multi-Frame VPS | ✅ Completed (`c664876`) |
| PROMPT 3 | Image Resize + JWT Auth | ✅ Completed (`184f608`) |
| PROMPT 4 Part A | Navigatus Resize + Race Fix | ✅ Completed (`184f608`, `978b624`) |
| PROMPT 4 Part B | WebXR NPM Package | ❌ **STILL OPEN** |
| PROMPT 5 | Unity SDK Expansion | ❌ **STILL OPEN** |
| PROMPT 6 | Frontend Multi-Frame + Navigatus Polish | ✅ Completed (`c664876`, `978b624`) |
| PROMPT 7 | CORS UI + Analytics | ✅ Completed (`4b76585`) |
| PROMPT 8 (NEW) | WebXR NPM Package (consolidated) | ❌ **OPEN** |
| PROMPT 9 (NEW) | Unity SDK Expansion (consolidated) | ❌ **OPEN** |
| PROMPT 10 (NEW) | End-to-End Validation | ❌ **OPEN** |
| PROMPT 11 (NEW) | Field Capture at Synthetic AOI | ❌ **OPEN** |

---

## ✅ PROMPT 1: Spatial Hints — COMPLETED

**Status:** Done in `184f608`
**Files modified:** `backend/api/routes_vps.py`, `backend/services/vps.py`, `backend/api/schemas.py`

hint_position, hint_radius, hint_floor_height, geo_hint all implemented and working.

---

## ✅ PROMPT 2: Multi-Frame VPS — COMPLETED

**Status:** Done in `c664876`
**Files modified:** `backend/api/routes_vps.py`, `backend/services/vps.py`, `backend/api/schemas.py`, `frontend/lib/api.ts`, `frontend/types/index.ts`, `navigatus/src/lib/vpsClient.ts`

`POST /vps/localize/multi` accepts 4-6 images, merges correspondences, single PnP solve. Navigatus has `localizeMultiVideoFrame()`.

---

## ✅ PROMPT 3: Image Resize + JWT Auth — COMPLETED

**Status:** Done in `184f608`
**Files modified:** `backend/utils/image.py`, `backend/api/auth.py`, `backend/api/routes_vps.py`, `backend/utils/config.py`, `backend/models/tenant.py`, `backend/models/api_key.py`, `navigatus/src/lib/vpsClient.ts`

1280px resize on both server and client. JWT multi-tenant with `require_scope()` replacing `validate_api_key` on VPS routes.

---

## ✅ PROMPT 4 Part A: Navigatus Resize + Race Fix — COMPLETED

**Status:** Done in `184f608` (resize), `978b624` (race fix + multi-frame warmup)
**Files modified:** `navigatus/src/lib/vpsClient.ts`, `navigatus/src/App.tsx`

Capture capped at 1280px. Multi-frame warmup on AR entry. `isLocalizingRef` prevents concurrent localizations.

---

## ❌ PROMPT 8 (was 4 Part B): WebXR NPM Package — OPEN

**File:** `packages/vps-webxr/` (new directory at repo root)

Create a minimal NPM package `@vps/web-client` that wraps the REST API for use by third-party developers.

```
packages/vps-webxr/
  package.json
  tsconfig.json
  src/
    index.ts          # exports
    VpsClient.ts      # main class
    types.ts          # interfaces
    websocket.ts      # optional WS sync
```

```typescript
// VpsClient.ts — mirrors navigatus's vpsClient.ts but as a proper NPM package
export class VpsClient {
  constructor(private baseUrl: string, private apiKey?: string) {}

  async localize(sceneId: string, image: Blob | HTMLVideoElement, options?: {
    hintPosition?: [number,number,number],
    hintRadius?: number,
  }): Promise<LocalizeResponse>

  async localizeMulti(sceneId: string, images: Blob[], options?: {
    hintPosition?: [number,number,number],
  }): Promise<MultiFrameLocalizeResponse>

  async getScene(sceneId: string): Promise<Scene>

  // WebSocket sync for multi-agent
  connectWebSocket(sceneId: string, agentId: string, onUpdate: (agents: Agent[]) => void): WebSocket
}
```

### Package.json
```json
{
  "name": "@vps/web-client",
  "version": "0.1.0",
  "main": "dist/index.js",
  "types": "dist/index.d.ts",
  "files": ["dist"],
  "scripts": {
    "build": "tsc",
    "prepublishOnly": "npm run build"
  }
}
```

### Build & Test
```bash
cd packages/vps-webxr
npm install
npm run build
# Verify in a test project:
cd /tmp && mkdir test-vps && cd test-vps
npm init -y
npm install /path/to/packages/vps-webxr
node -e "const { VpsClient } = require('@vps/web-client'); console.log('OK');"
```

### Types to mirror (from backend schemas)
- `LocalizeResponse`: position, rotation, inliers, confidence, hint_used
- `MultiFrameLocalizeResponse`: same + frames_used, frame_confidences
- `Scene`: id, name, status, splat_path, etc.
- `AgentPoseUpdate`: agent_id, position, rotation

### Acceptance Criteria
- [ ] `npm install @vps/web-client` works in a fresh Vite/CRA project
- [ ] `const client = new VpsClient(url, key); await client.localize(sceneId, blob)` returns pose
- [ ] TypeScript types exported properly
- [ ] WebSocket sync helper works in browser
- [ ] Published to npm or installable from local path

---

## ❌ PROMPT 9 (was 5): Unity SDK Expansion — OPEN

**Files:** `unity-sdk/com.vps.sdk/Runtime/Scripts/*`, `unity-sdk/com.vps.sdk/Samples/*`

### Goal
Turn the bare VpsClient into a proper Unity SDK with 3 sample scenes:

### 1. LocalizationSample
- AR scene that captures camera frames via `WebCamTexture`
- Calls VPS `POST /vps/localize` with the frame
- Aligns content to `MapSpace` using returned pose
- Shows confidence/inlier HUD

### 2. NavigationSample
- Unity NavMesh on the map mesh (or generated ground plane)
- `NavMeshAgent` driven by VPS pose updates
- Target selection UI (tap to set destination)
- Path visualization line renderer
- Step-by-step arrow indicators

### 3. MultiFrameSample
- Captures 4 frames at 0.5s intervals
- Sends to `POST /vps/localize/multi`
- Shows per-frame confidence bars
- Combined pose overlay

### Structure
```
Samples~/
  Localization/
    LocalizationSample.unity
    LocalizationController.cs
    README.md
  Navigation/
    NavigationSample.unity
    NavigationController.cs
    README.md
  MultiFrame/
    MultiFrameSample.unity
    MultiFrameController.cs
    README.md
```

### CoordinateConverter must handle
- LHS (Unity) ↔ RHS (COLMAP/OpenCV) for poses
- Multi-frame confidence overlay in AR

### VPSClient.cs additions
- Add hint params to all localization methods
- Add multi-frame endpoint wrapper

### Acceptance Criteria
- [ ] LocalizationSample builds and runs on Quest 3 / Android device
- [ ] NavigationSample shows path from current VPS pose to target
- [ ] MultiFrameSample shows improved accuracy over single-frame
- [ ] Coordinate Converter handles LHS↔RHS correctly

---

## ❌ PROMPT 10: End-to-End Validation — OPEN

**Goal:** Validate that all Phase 1 features work together end-to-end.

### Test Matrix

| Test | Scenario | Expected | Script |
|---|---|---|---|
| T1 | Upload video → process → READY | `scene.status == "READY"` | `curl -X POST /scene/upload -F "file=@test.mp4"` |
| T2 | Single-frame localize | Returns pose with inliers ≥ 20 | `curl -X POST /vps/localize -F "scene_id=..." -F "query_image=@frame.jpg"` |
| T3 | Spatial hint: hintPosition | Faster, fewer matches | Same as T2 + `-F "hint_position=[1,2,3]" -F "hint_radius=10"` |
| T4 | Spatial hint: hintFloorHeight | Filters to Y-band | Same as T2 + `-F "hint_floor_height=[0,3]"` |
| T5 | Spatial hint: geoHint | Graceful skip | Same as T2 + `-F "geo_hint={\"lat\":3.15,\"lng\":101.7}"` |
| T6 | Multi-frame with 4 images | Returns frames_used ≥ 2 | `curl -X POST /vps/localize/multi -F "scene_id=..." -F "image1=@f1.jpg" -F "image2=@f2.jpg" ...` |
| T7 | JWT auth: valid token | 200 OK | `curl -H "Authorization: Bearer $TOKEN" ...` |
| T8 | JWT auth: invalid token | 401 | `curl -H "Authorization: Bearer bad" ...` |
| T9 | JWT auth: missing scope | 403 | Token with "read" scope trying to upload |
| T10 | Image resize: 4K input | Resized to ≤1280px before feature extraction | Upload 4K image, check logs |

### Acceptance Criteria
- [ ] All T1-T10 pass
- [ ] Log output confirms resize happening
- [ ] Multi-frame succeeds where single-frame fails (test in corridor)
- [ ] No regressions on existing functionality

---

## ❌ PROMPT 11: Field Capture at Synthetic AOI — OPEN

**Goal:** Capture real-world video at target AOIs to validate synthetic-to-real transfer.

### Target Locations (KL)
1. **KLCC** — Suria KLCC, KLCC Park area
2. **Bukit Bintang** — Pavilion, Starhill, intersection area
3. **Merdeka Square** — Dataran Merdeka, Sultan Abdul Samad Building

### Capture Protocol
```
For each location:
  1. Walk slowly (0.5m/s) covering 50-100m path
  2. Capture video at 1080p 30fps (use Navigatus record feature)
  3. Capture 5-10 individual frames at known positions
  4. Note: time of day, lighting conditions, foot traffic
```

### Upload & Process
```bash
# Upload each video to VPS backend
curl -X POST http://100.118.54.14:8000/scene/upload \
  -F "file=@klcc_walk_01.mp4" \
  -F "name=KLCC Walk 1"

# Trigger processing
curl -X POST http://100.118.54.14:8000/scene/{id}/process

# Test localization with captured frames
curl -X POST http://100.118.54.14:8000/vps/localize \
  -F "scene_id={id}" \
  -F "query_image=@klcc_frame_01.jpg"
```

### What to Validate
1. Does synthetic data transfer to real-world scenes?
2. How many frames needed for reliable localization?
3. What's the accuracy vs ground truth (GPS + visual landmarks)?
4. Does multi-frame improve over single-frame in real conditions?
5. Do spatial hints help in large open areas (KLCC)?

### Acceptance Criteria
- [ ] At least 3 videos captured and processed per location
- [ ] Localization success rate documented per location
- [ ] Comparison table: single-frame vs multi-frame accuracy
- [ ] Known failure cases identified and documented
