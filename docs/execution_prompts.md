# Phase 1 — Parallel Task Prompts

All 4 tasks work on **different files** — no merge conflicts. Execute in parallel.

---

## PROMPT 1: PC Agent 1 — Spatial Hints (3-4 days)

**Files:** `backend/api/routes_vps.py`, `backend/services/vps.py`, `backend/api/schemas.py`

### Goal
Add 4 optional spatial hints to the `/vps/localize` endpoint to narrow FAISS search scope, improve accuracy, and reduce latency in large scenes.

### 1. Update `backend/api/schemas.py`

Add new fields to `LocalizeResponse`:
```python
class LocalizeResponse(BaseModel):
    position: list[float]
    rotation: list[float]
    inliers: int
    confidence: float
    # NEW:
    hint_used: str | None = None  # e.g. "hintPosition", "geoHint", null
```

### 2. Update `backend/api/routes_vps.py` — Add optional form params to `POST /vps/localize`

```python
@router.post("/localize", response_model=LocalizeResponse, dependencies=[Depends(validate_api_key)])
async def localize(
    scene_id: str = Form(...),
    query_image: UploadFile = File(...),
    agent_id: str | None = Form(None),
    # NEW optional hint params:
    hint_position: str | None = Form(None),   # JSON "[x, y, z]"
    hint_radius: float | None = Form(None),    # meters, default 25
    hint_floor_height: str | None = Form(None), # JSON "[y_min, y_max]"
    geo_hint: str | None = Form(None),          # JSON "{lat, lng, alt}"
    db: Session = Depends(get_db),
) -> LocalizeResponse:
    settings = get_settings()
    query_path = save_upload(query_image, f"queries/{scene_id}")
    try:
        result = VPSService.localize(
            scene_id=scene_id,
            query_image_path=query_path,
            db=db,
            hint_position=json.loads(hint_position) if hint_position else None,
            hint_radius=hint_radius or 25.0,
            hint_floor_height=json.loads(hint_floor_height) if hint_floor_height else None,
            geo_hint=json.loads(geo_hint) if geo_hint else None,
        )
        ... [rest same: broadcast if agent_id, return result]
```

### 3. Update `backend/services/vps.py` — Modify `localize_image()` and `_localize_with_feature_set()`

**In `localize_image()`:**
- Accept new params and pass them through to `_localize_with_feature_set()`

**In `_localize_with_feature_set()`:**
- After loading metadata and before FAISS `index.search()`:
  1. **If hint_position + hint_radius given:** Filter `points3d` to keep only points within hint_radius meters of hint_position. Also filter `point3d_ids` correspondingly. Rebuild a temporary FAISS index with only these points (or simply reduce the search space).
  
  Implementation approach (simpler):
  ```python
  if hint_position is not None:
      pos = np.array(hint_position, dtype=np.float32)
      dists = np.linalg.norm(points3d - pos, axis=1)
      within_radius = dists < hint_radius
      if within_radius.any():
          # Filter metadata to only points within radius
          points3d = points3d[within_radius]
          point3d_ids = point3d_ids[within_radius]
          # Must rebuild index with filtered descriptors
          all_descriptors = ... # Load original descriptors
          filtered_descs = all_descriptors[within_radius]
          index = faiss.IndexFlatL2(filtered_descs.shape[1])
          index.add(filtered_descs)
  ```

  2. **If hint_floor_height given:** Parse `[y_min, y_max]`. Filter `points3d` to keep only points where Y is within the band. Same index filtering as above.
  
  3. **If geo_hint given:** For now, convert GPS → approximate scene position using the scene's stored reference point (if available). If no reference point, fall back to no hint. This is a best-effort feature.

  4. **Track which hint was used** — set `hint_used` in the result dict.

### 4. Update Unity SDK `VPSClient.cs`

Add optional hint parameters to the `Localize()` methods (can be done by PC Agent 1 or deferred to the Unity expansion task).

### Acceptance Criteria
- [x] `curl -X POST ... -F "hint_position=[1,2,3]" -F "hint_radius=10"` returns faster on large scenes
- [x] `hint_floor_height=[0,3]` filters to ground-floor features only
- [x] `geo_hint={"lat":3.15,"lng":101.7}` degrades gracefully if no geo ref
- [x] No hint = existing behavior preserved exactly

---

## PROMPT 2: PC Agent 2 — Multi-Frame VPS (5 days)

**Files:** `backend/api/routes_vps.py`, `backend/services/vps.py`, `backend/api/schemas.py`, `frontend/lib/api.ts`, `frontend/types/index.ts`, `navigatus/src/lib/vpsClient.ts`

### Goal
Add `POST /vps/localize/multi` accepting 4-6 images for more robust pose estimation in challenging environments.

### 1. Add schema in `backend/api/schemas.py`

```python
class MultiFrameLocalizeResponse(BaseModel):
    position: list[float]
    rotation: list[float]
    inliers: int
    confidence: float
    frames_used: int       # how many of the submitted frames contributed
    frame_confidences: list[float]  # per-frame confidence for debugging
```

### 2. Add route in `backend/api/routes_vps.py`

```python
@router.post("/localize/multi", response_model=MultiFrameLocalizeResponse, dependencies=[Depends(validate_api_key)])
async def localize_multi(
    scene_id: str = Form(...),
    image1: UploadFile = File(...),
    image2: UploadFile = File(...),
    image3: UploadFile = File(...),
    image4: UploadFile = File(...),
    image5: UploadFile | None = File(None),
    image6: UploadFile | None = File(None),
    agent_id: str | None = Form(None),
    hint_position: str | None = Form(None),
    hint_radius: float | None = Form(None),
    hint_floor_height: str | None = Form(None),
    db: Session = Depends(get_db),
) -> MultiFrameLocalizeResponse:
    # Save all images
    # Call VPSService.localize_multi()
    # Broadcast if agent_id
    # Return result
```

### 3. Add method in `backend/services/vps.py`

```python
@staticmethod
def localize_multi(
    scene_id: str,
    query_image_paths: list[Path],
    db: Session,
    # optional hints same as single-frame
) -> dict:
    """Localize using 4-6 images for improved robustness.
    
    Strategy:
    1. For each image, extract features and match against FAISS index
    2. Collect 2D-3D correspondences from each frame
    3. Merge ALL correspondences into a single PnP RANSAC solve
    4. A frame is "contributing" if it produces ≥10 inliers on its own
    5. Return refined pose with combined confidence
    """
```

Implementation details:
- Process each image through the same `_localize_with_feature_set` path but **don't fail early** — collect results from all frames
- After collecting correspondences from all frames, do a single `solvePnPRansac` with all object_points/image_points
- `frames_used` = how many frames had ≥10 inliers
- `frame_confidences` = per-frame inlier ratio
- Apply calibration to the final combined result
- If overall inliers < MIN_INLIERS, reject

### 4. Add fallback logic

If only 1-3 images provided (e.g., camera lost tracking), fall back to single-frame `/vps/localize` with the best image.

### 5. Update `frontend/lib/api.ts`

```typescript
async localizeMulti(sceneId: string, images: File[], hintPosition?: [number,number,number]): Promise<MultiFrameLocalizeResponse>
```

### 6. Update `frontend/types/index.ts`

Add `MultiFrameLocalizeResponse` interface.

### 7. Update `navigatus/src/lib/vpsClient.ts`

Add `localizeMultiVideoFrame()` that captures 4 frames at 0.5s intervals, then sends them together.

### Acceptance Criteria
- [x] `POST /vps/localize/multi` with 4 images returns a pose
- [x] Multi-frame succeeds where single-frame fails (test in repetitive corridor)
- [x] Response includes `frames_used` and `frame_confidences`
- [x] Navigatus can collect and send 4 frames
- [x] Works with hint params too

---

## PROMPT 3: PC Agent 3 — Image Resize Middleware → JWT Auth (5 days)

**Files:** `backend/api/main.py`, `backend/api/auth.py`, `backend/api/routes_vps.py`, `backend/utils/config.py`, `navigatus/src/lib/vpsClient.ts`

### Part A: Image Resolution Limit (1 day)

**Backend middleware** — Add a utility or middleware that resizes query images to max 1280px on longest side:

```python
# backend/utils/image.py or inline in vps.py
import cv2

def resize_if_needed(image_path: Path, max_dim: int = 1280) -> Path:
    """Resize image so max(width, height) <= max_dim. Returns path to resized image."""
    img = cv2.imread(str(image_path))
    h, w = img.shape[:2]
    if max(h, w) <= max_dim:
        return image_path
    scale = max_dim / max(h, w)
    new_w, new_h = int(w * scale), int(h * scale)
    resized = cv2.resize(img, (new_w, new_h))
    resized_path = image_path.parent / f"{image_path.stem}_resized{image_path.suffix}"
    cv2.imwrite(str(resized_path), resized)
    return resized_path
```

Apply it in `VPSService._localize_with_feature_set()` — right before extracting features from the query image.

**Navigatus client-side** — In `captureVideoFrame()` in `navigatus/src/lib/vpsClient.ts`, add resize before canvas.toBlob:

```typescript
const MAX_DIM = 1280;
let { width, height } = video;
if (Math.max(width, height) > MAX_DIM) {
  const scale = MAX_DIM / Math.max(width, height);
  canvas.width = Math.round(width * scale);
  canvas.height = Math.round(height * scale);
} else {
  canvas.width = width;
  canvas.height = height;
}
```

This reduces payload from ~400KB (4K) to ~100KB (720p), cutting upload time and FAISS search cost.

### Part B: JWT Multi-Tenant Auth (4 days)

**Files:** `backend/api/auth.py`, `backend/utils/config.py`, `backend/models/tenant.py`, `backend/api/main.py`, `backend/api/routes_auth.py`

Replace the current API-key-only auth with JWT:
- New endpoint `POST /auth/token` — accepts `client_id` + `client_secret`, returns JWT with 30min expiry (match MultiSet's model)
- New `validate_jwt()` dependency — checks Bearer token, extracts `tenant_id`, `scope` (query/write/delete)
- Add `Tenant` model and `ApiKey` model to DB
- Backward compat: existing `X-API-Key` header continues to work but logs deprecation warning
- Scopes: write=upload+process, query=localize+read, delete=cleanup

Keep it simple — no user registration UI yet, just API-level multi-tenancy so different teams can have different API keys with different permissions.

### Acceptance Criteria
- [x] Images >1280px auto-resized before feature extraction
- [x] Navigatus captures at ≤1280px
- [x] `POST /auth/token` returns JWT
- [x] `Authorization: Bearer <jwt>` works alongside legacy `X-API-Key`
- [x] Scope enforcement: read-only key can't upload/delete

---

## PROMPT 4: Mac Agent — Navigatus Resize + WebXR NPM Package

### Part A: Navigatus Resolution Cap (1 day)

**File:** `navigatus/src/lib/vpsClient.ts`

Apply the same resize logic as PC Agent 3 Part A (client-side only) in `captureVideoFrame()`.

**File:** `navigatus/src/App.tsx`

Fix the fragile camera restart on resolution change (line ~1240-1244):
- Replace `setTimeout(startRecordCamera, 100)` with proper lifecycle — stop old stream, await new getUserMedia, set new stream.
- Also fix: camera preview should remain active when settings panel is open (currently stops).

### Part B: WebXR NPM Package (4 days)

**New package** at `packages/vps-webxr/`

Create a minimal NPM package `@vps/web-client` that wraps the REST API:

```
packages/vps-webxr/
  package.json
  tsconfig.json
  src/
    index.ts          # exports
    VpsClient.ts      # main class
    types.ts          # interfaces
    websocket.ts      # optional WS sync
  README.md
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

Package.json:
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

Also update the frontend's `frontend/lib/api.ts` to optionally use this package (or keep existing axios-based client — the NPM package should be a standalone thing developers can use in their own projects).

### Acceptance Criteria
- [x] Navigatus camera restart is robust (no race conditions)
- [x] `npm install @vps/web-client` works in a fresh Vite/CRA project
- [x] `const client = new VpsClient(url, key); await client.localize(sceneId, videoElement)` returns pose
- [x] TypeScript types exported properly
- [x] WebSocket sync helper works in browser

---

## Phase 2 Prompts (execute after Phase 1 completes)

---

## PROMPT 5: PC Agent 1 — Unity SDK Expansion (10 days)

**Files:** `unity-sdk/com.vps.sdk/Runtime/Scripts/*`, `unity-sdk/com.vps.sdk/Samples/*`

### Goal
Turn the bare VpsClient into a proper Unity SDK with sample scenes:
1. **LocalizationSample** — AR scene that captures camera frames, calls VPS, aligns MapSpace
2. **NavigationSample** — NavMesh-based pathfinding from current pose to target
3. **MultiFrameSample** — Uses multi-frame API for robust first localization

Create `Samples~/Localization/`, `Samples~/Navigation/`, `Samples~/MultiFrame/` with:
- `.unity` scene files
- `.prefab` for AR session setup
- `.cs` sample scripts
- README per sample

### Navigation specifically:
- Unity NavMesh on the map mesh (if available) or on a generated ground plane
- `NavMeshAgent` driven by VPS pose updates
- Target selection UI
- Path visualization line renderer

### CoordinateConverter must handle:
- LHS (Unity) ↔ RHS (COLMAP/OpenCV) for poses
- Multi-frame confidence overlay in AR

---

## PROMPT 6: PC Agent 2 — Frontend Multi-Frame + Navigatus Polish (3 days)

**Files:** `frontend/app/localize/page.tsx`, `frontend/lib/api.ts`, `navigatus/src/App.tsx`

1. **Frontend localize page**: Add "Multi-Frame" tab — captures 4 webcam frames at 0.5s intervals, sends to `/vps/localize/multi`, displays per-frame confidence + combined result
2. **Navigatus AR view**: Add multi-frame collection before the initial localization (collect 4 frames silently, then send in one request for faster first lock)
3. **Navigatus import fix**: Fix the `setTimeout(startRecordCamera, 100)` race condition on resolution change

---

## PROMPT 7: PC Agent 3 — CORS UI + Basic Analytics (4 days)

**Files:** `frontend/app/settings/page.tsx` (new), `frontend/app/analytics/page.tsx` (new), `backend/api/routes_scene.py`, `backend/api/routes_vps.py`

1. **CORS UI (`/settings`):**
   - Allowlist of allowed origins
   - Backend reads from `CORS_ALLOWED_ORIGINS` env var or DB
   - UI to add/remove origins

2. **Basic Analytics (`/analytics`):**
   - Query counter per scene (track in Redis)
   - Success/failure rate per scene (count successful `/vps/localize` vs 404/400 errors)
   - Simple dashboard: bar chart of queries/day using Chart.js or recharts
   - Latency histogram (p50, p95, p99 response time)

3. **Backend metrics middleware** — decorator that increments Redis counters on each VPS query
