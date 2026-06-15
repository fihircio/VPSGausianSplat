# Coordinate Conversion & Localization Confidence Reference

This document covers the three coordinate systems used across the VPS stack, how to convert between them, how localization output maps to Unity `Transform`, and how to interpret confidence scores.

---

## 1. Coordinate Systems

### 1.1 WGS84 — GPS Latitude / Longitude / Altitude

The standard geospatial reference used for GPS and mapping APIs. All AOI origins in `aoi_registry.json` are stored in WGS84.

```
lat  = degrees north of equator  (−90 … +90)
lon  = degrees east of prime meridian  (−180 … +180)
h    = height above WGS84 ellipsoid in metres
```

**When we use it:** AOI origin definition, Google 3D tile request coordinates.

---

### 1.2 ECEF — Earth-Centred Earth-Fixed (metres)

A Cartesian frame with origin at Earth's centre. Used as a conversion intermediate.

```
         Z (North Pole)
         │
         │
         │
─────────┼────── X (0°N 0°E, equator/prime meridian)
        /│
       / │
      /  │
     Y (90°E, equator)
```

Conversion from WGS84 (implemented in [transforms.py](file:///Users/fihiromar/Desktop/WORKS/20260308_VPSMAP/WIP/backend/services/google3d/transforms.py)):

```python
from backend.services.google3d.transforms import wgs84_to_ecef, WGS84Point

ecef = wgs84_to_ecef(WGS84Point(lat=3.1480, lon=101.6934, h=50.0))
# ECEFPoint(x=..., y=..., z=...)
```

**When we use it:** Intermediate frame only — never used directly in the API response.

---

### 1.3 ENU — East / North / Up (metres, local tangent plane)

A local Cartesian frame tangent to the WGS84 ellipsoid at a chosen **origin** point. This is what camera path generation operates in — it avoids the curvature of ECEF for small areas (< ~50 km).

```
           U (Up)
           │
           │
           │
───────────┼──────── N (North)
          /│
         / │
        /  │
       E (East)
```

All three axes are in **metres** relative to the origin.

```python
from backend.services.google3d.transforms import wgs84_to_enu, WGS84Point

origin = WGS84Point(lat=3.1480, lon=101.6934, h=50.0)
point  = WGS84Point(lat=3.1490, lon=101.6940, h=52.0)

enu = wgs84_to_enu(point, origin)
# ENUPoint(e=+67.2, n=+111.3, u=+2.0)  ← approx
```

**When we use it:** Generating synthetic camera paths for AOIs.

---

### 1.4 COLMAP Scene Space (metres)

The coordinate system that COLMAP assigns to a reconstructed 3D map. Its origin, scale, and orientation are **arbitrary** — they depend on which camera was used as the reference frame during reconstruction.

> **Important:** COLMAP scene space is NOT aligned to WGS84 / ENU / Unity world space by default. The only guarantee is that it is metric (1 unit = 1 metre) after running `colmap model_aligner` with GPS priors.

**VPS localization output is always in COLMAP scene space.** Your application is responsible for the transform from scene space to Unity world space.

---

## 2. Full Transform Chain

```
GPS (WGS84)
    │  wgs84_to_ecef()
    ▼
ECEF
    │  ecef_to_enu()
    ▼
ENU (local, metres)   ← AOI camera path generation lives here
    │  [manual alignment at scan time]
    ▼
COLMAP Scene Space    ← VPS localization output lives here
    │  [your scene anchor transform in Unity]
    ▼
Unity World Space     ← AR object placement lives here
```

---

## 3. Applying Localization Pose in Unity

### 3.1 The VPS Scene Anchor pattern

Place an empty GameObject (`VPSSceneAnchor`) in your Unity scene at a world position and rotation that corresponds to the **origin of the COLMAP map** (typically the first camera position used during scanning).

```
Unity World Space
┌──────────────────────────────────────┐
│                                      │
│   VPSSceneAnchor (0,0,0 in scan)     │
│         │                            │
│         │  TransformPoint(scenePos)  │
│         ▼                            │
│   AR object placed here              │
│                                      │
└──────────────────────────────────────┘
```

```csharp
// localized pose from VPS in scene space
Vector3    scenePos = new Vector3(response.x, response.y, response.z);
Quaternion sceneRot = new Quaternion(response.qx, response.qy, response.qz, response.qw);

// transform into Unity world space via anchor
transform.position = sceneAnchor.TransformPoint(scenePos);
transform.rotation = sceneAnchor.rotation * sceneRot;
```

### 3.2 Position vs Rotation

| VPS field | Meaning | Unity mapping |
|---|---|---|
| `x`, `y`, `z` | Camera position in COLMAP scene space (metres) | `transform.position` via anchor |
| `qx`, `qy`, `qz`, `qw` | Camera rotation quaternion (COLMAP convention) | `transform.rotation` via anchor |

> **COLMAP uses a right-handed coordinate system with Y pointing down.** Unity uses left-handed with Y pointing up. You may need to apply a coordinate flip depending on how your scan was captured. A common fix:
>
> ```csharp
> // Flip Y and Z to convert from COLMAP right-handed to Unity left-handed
> scenePos = new Vector3(response.x, -response.y, response.z);
> ```
>
> Confirm empirically with a test scene before deploying.

---

## 4. Localization Confidence & Error Scoring

### 4.1 Confidence Thresholds

| Condition | Status | Meaning | Recommended action |
|---|---|---|---|
| `inliers > 30` AND `confidence > 0.50` | **Locked** ✅ | Strong geometric match. High accuracy. | Apply pose, show AR content. |
| `inliers >= 15` AND `confidence >= 0.30` | **Weak** ⚠️ | Marginal match. Usable but uncertain. | Apply pose, show "searching…" UI, do not trigger important actions. |
| Otherwise | **Failed** ❌ | Too few matches. Unreliable. | Discard response. Retry or prompt user to move. |

These thresholds are also documented in `backend/services/vps_service.py`. Do not hard-code different values in your Unity project — the backend and client must agree.

### 4.2 Confidence Score Calculation

`confidence` is derived from the inlier ratio after RANSAC PnP:

```
confidence = num_inliers / num_candidates   (clamped to [0.0, 1.0])
```

A high `confidence` with low `inliers` (e.g. confidence=0.9 but inliers=5) can happen in feature-sparse scenes and is still treated as **failed** because the absolute inlier count is too low for a reliable geometric fix.

### 4.3 Error Metrics (Evaluation Reports)

After a pilot evaluation, the accuracy report contains:

| Field | Unit | Description |
|---|---|---|
| `translation_error` | metres | Euclidean distance between predicted and ground-truth camera position |
| `rotation_error` | degrees | Angular difference between predicted and ground-truth camera rotation |
| `success_rate` | fraction [0–1] | Fraction of queries where `translation_error < threshold` |
| `inliers_mean` | count | Mean inliers across all successful queries |

**Typical targets for Pilot tier:**

| Metric | Target |
|---|---|
| `translation_error` median | < 0.30 m |
| `translation_error` p95 | < 0.80 m |
| `rotation_error` median | < 8° |
| `success_rate` | ≥ 0.70 |

---

## 5. Using the Python Transform Utilities

The backend helpers in [transforms.py](file:///Users/fihiromar/Desktop/WORKS/20260308_VPSMAP/WIP/backend/services/google3d/transforms.py) can be imported directly for offline scripts or evaluation:

```python
from backend.services.google3d.transforms import (
    WGS84Point, ECEFPoint, ENUPoint,
    wgs84_to_ecef, ecef_to_wgs84,
    wgs84_to_enu,  enu_to_wgs84,
)

# Example: convert two GPS points to ENU offset (useful for anchor distance checks)
origin = WGS84Point(lat=3.1480, lon=101.6934, h=50.0)
target = WGS84Point(lat=3.1490, lon=101.6934, h=50.0)
enu = wgs84_to_enu(target, origin)
print(f"North offset: {enu.n:.2f} m")   # ≈ 111 m per 0.001° lat
```

No external dependencies required — the module uses only Python `math`.

---

## 6. Quick ASCII Reference

```
WGS84 (lat/lon/h)
│
├─ wgs84_to_ecef() ──► ECEF (x/y/z in metres from Earth centre)
│                           │
│                           └─ ecef_to_enu(origin) ──► ENU (e/n/u in metres)
│                                                           │
│                                                           └─ camera paths,
│                                                              synthetic frames
│
└─ VPS output (COLMAP scene space, metres)
        │
        └─ via Unity sceneAnchor.TransformPoint()
                │
                └─ Unity world space → AR object placement
```
