# Quickstart: From Video to 6DoF Pose in 5 Minutes

Turn a phone recording into a localizable AR scene. No SDK installs, no GPU required for basic evaluation.

---

## 1. Record a Scene

Use any phone camera:

- **Resolution**: 1080p @ 30fps
- **Height**: 1.4–1.6m (natural walking height)
- **Motion**: Walk at slow pace, keep camera steady
- **Coverage**: 2 complete loops of the area (clockwise + counter-clockwise)
- **Duration**: 30–120 seconds

> Full capture guide: [`capture_protocol.md`](capture_protocol.md)

---

## 2. Upload

```bash
curl -X POST http://localhost:8000/scene/upload \
  -H "X-API-Key: YOUR_API_KEY" \
  -F "file=@corridor.mp4" \
  -F "name=hospital-corridor"
```

**Response:**
```json
{
  "id": "bcaa4187-b6f0-4d4c-8996-b234ba0af8e1",
  "name": "hospital-corridor",
  "status": "UPLOADED",
  "input_type": "video",
  "frame_count": 0
}
```

Save the `id` — you'll need it for all subsequent steps.

---

## 3. Process

Triggers: frame extraction → COLMAP SfM → FAISS feature index → Gaussian splat export.

```bash
curl -X POST http://localhost:8000/scene/<SCENE_ID>/process \
  -H "X-API-Key: YOUR_API_KEY"
```

Poll status every 30 seconds:

```bash
curl http://localhost:8000/scene/<SCENE_ID>
```

Wait for `"status": "DONE"`. Processing time depends on video length and available GPU.

**Statuses**: `UPLOADED` → `PROCESSING` → `DONE` (or `FAILED`)

---

## 4. Localize a Query Image

Take a new photo of the same space and localize it:

```bash
curl -X POST http://localhost:8000/vps/localize \
  -H "X-API-Key: YOUR_API_KEY" \
  -F "scene_id=<SCENE_ID>" \
  -F "query_image=@new-photo.jpg"
```

**Response:**
```json
{
  "position": [1.23, -0.51, 2.07],
  "rotation": [0.01, 0.72, -0.03, 0.69],
  "confidence": 0.78,
  "inliers": 42
}
```

| Field | Meaning |
|-------|---------|
| `position` | Camera XYZ in scene coordinates (meters) |
| `rotation` | Camera orientation as quaternion [w, x, y, z] |
| `confidence` | Inlier ratio — fraction of feature matches that survived PnP RANSAC |
| `inliers` | Number of 2D–3D correspondences that passed RANSAC |

**Quality guide:**
| confidence | inliers | Meaning |
|------------|---------|---------|
| ≥ 0.5 | ≥ 30 | **Locked** — reliable pose |
| ≥ 0.3 | ≥ 15 | **Weak** — usable with caution |
| < 0.3 | < 15 | **Failed** — recapture or improve scene |

---

## 5. View in Browser (Portal)

Open `http://localhost:3000` in your browser:

- **Dashboard** — see all scenes, processing status, frame counts
- **Scene Detail** — view 3D point cloud, splat preview, anchors
- **Localize** — upload a query image and see the estimated pose + accuracy metrics
- **Upload** — upload new scenes directly from the UI

---

## 6. Deploy to Mobile (Navigatus)

The Navigatus PWA runs on any smartphone browser:

```bash
cd navigatus
cp .env.example .env
# Set REACT_APP_VPS_API_BASE_URL to your backend URL
npm start
```

Open `http://localhost:3001` on your phone (same WiFi) to see:
- Hospital destination search
- AR navigation with live VPS localization (camera → 6DoF pose every 4s)
- In-app scene recording with upload

---

## 7. Integrate via Unity SDK

```csharp
using VPSGaussianSplat;
using UnityEngine;

var client = new VpsClient("https://your-api.com", "your-api-key");
VpsPose pose = await client.LocalizeAsync("scene-id", capturedTexture);
transform.position = pose.Position;
transform.rotation = pose.Rotation;
```

See [`docs/unity_sdk/`](../unity_sdk) for the full Unity package.

---

## Next Steps

- [Capture Protocol](capture_protocol.md) — how to record production-quality scenes
- [Demo Walkthrough](demo_walkthrough.md) — full end-to-end demonstration script
- [API Contract](api_contract.md) — complete endpoint reference
- [Validation Checklist](validation_checklist.md) — accuracy benchmarks and reporting
- [90-Day Plan](commercialization_90_day_plan.md) — commercial roadmap and milestones
