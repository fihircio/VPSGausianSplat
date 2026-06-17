# Competitive Comparison: VPSGaussianSplat vs Alternatives

## Overview

| | VPSGaussianSplat | MultiSet.ai | 8thWall (Niantic) | Immersal (Hexagon) | Apple ARKit |
|---|---|---|---|---|---|
| **Core tech** | Gaussian Splatting + SfM + FAISS | Neural VPS | Visual positioning + mesh | SLAM + mesh | ARWorldMap + mesh |
| **Visual quality** | ★★★★★ Photorealistic GSplat | ★★★ Mesh | ★★★ Standard mesh | ★★★ Standard mesh | ★★★ Standard mesh |
| **VPS accuracy** | ~4cm avg (0.036m) | ~6cm median, drift <1cm @10m / <6cm @100m | ~10-50cm | ~10-30cm | ~10-50cm |
| **Indoor support** | ✅ Built for it | ✅ | ❌ GPS-focused | ✅ | ❌ Limited |
| **Self-hostable** | ✅ Open source | ⚠️ Enterprise on-prem only | ❌ | ❌ | ❌ |
| **Open API** | ✅ REST + WebSocket | ✅ REST | ✅ REST | ✅ REST | ❌ iOS only |
| **Capture methods** | Phone video, in-app recording | LiDAR app, 360 cam, E57 scanners, GSplat import | Phone camera | LiDAR app, E57 scanners | ARKit session |
| **Rendering in-view** | Real-time Gaussian Splatting | Textured mesh | Textured mesh | Textured mesh | Textured mesh |

---

## Detailed Feature Comparison

### 1. Rendering & Visual Quality

**VPSGaussianSplat** uses Gaussian Splatting for real-time photorealistic novel view synthesis. Spaces render with photographic quality — no mesh simplification, no texture atlasing artifacts. Orders of magnitude smaller than NeRF.

**MultiSet** renders textured meshes in-view via MapMeshHandler in Unity. Gaussian Splatting is accepted as input (v1.12.0) but only to build VPS maps — the viewer still renders mesh. No neural or splat rendering in the runtime visualization.

**8thWall/Immersal/ARKit** all use standard textured meshes. Lower fidelity, visible artifacts at close range.

### 2. VPS Engine

**VPSGaussianSplat:**
- ORB/SIFT → FAISS index → Lowe's ratio test → PnP RANSAC → 6DoF pose
- Open pipeline: swap extractors (ORB → SIFT → SuperPoint → LightGlue), tune per scene, debug failures
- ~4cm avg error (KLCC benchmark)

**MultiSet (neural VPS):**
- Proprietary neural VPS, ~6cm median error
- Drift bounds: <1cm under 10m, <6cm at 100m
- Gen2 (v2.0.0, June 2026): improved recall in repetitive areas (corridors, basements, train stations)
- Multi-frame and single-frame query
- On-device localization: iOS (v1.10.0) + Android (v1.14.0)
- Localization filters: hintPosition, hintFloorHeight, hintRadius, geoHint, use2DFiltering, hintMapCodes
- Confidence scoring using multiple metrics (v1.12.0+)

### 3. Map Management

| Feature | VPSGaussianSplat | MultiSet |
|---------|-----------------|----------|
| Map versioning | Manual | ✅ Automated (v1.14.0) |
| Map merging | Manual | ✅ MapSet overlap + manual (VPS-powered since v1.14.0) |
| MapSets (multi-map) | ❌ | ✅ |
| Georeferencing (WGS84) | ❌ | ✅ |
| Analytics dashboard | ❌ | ✅ Query analytics, success heatmaps (v1.10.0+) |
| Raw mesh download | ✅ (COLMAP output) | ✅ (.glb, v1.1.0) |
| Map archiving | ❌ | ✅ (v1.10.0) |

### 4. Capture Methods

| Method | VPSGaussianSplat | MultiSet |
|--------|-----------------|----------|
| Phone video (RGB) | ✅ Primary method | ❌ (LiDAR required) |
| In-app recording | ✅ (navigatus PWA) | ❌ (separate app) |
| 360 video | ❌ | ✅ Insta360 X4/X5 (v1.14.0→2.0.0) |
| E57 scanners | ❌ | ✅ Leica, Matterport, NavVis, Faro, Xgrids |
| Gaussian Splat import | ✅ Native format | ✅ As VPS map source (v1.12.0) |
| LiDAR scanning | ❌ | ✅ Mobile app / Unity SDK |
| Matterpak | ❌ | ✅ (v1.9.2) |

### 5. Deployment Model

| | Self-host | Cloud SaaS | Mobile SDK | Web SDK | Unity SDK | XR SDK |
|---|---|---|---|---|---|---|
| **VPSGaussianSplat** | ✅ Open source | ✅ (planned) | ✅ (PWA) | ✅ Three.js | ✅ | ❌ |
| **MultiSet** | ⚠️ Enterprise on-prem | ✅ | ✅ Native (iOS/Android) | ✅ WebXR (NPM) | ✅ | ✅ Quest + Ray-Ban |
| **8thWall** | ❌ | ✅ | ✅ | ✅ | ✅ | ❌ |
| **Immersal** | ❌ | ✅ | ✅ Native | ❌ | ✅ | ❌ |
| **ARKit** | ❌ | ❌ | ❌ iOS only | ❌ | ❌ | ❌ |

### 6. Pricing

| Product | Model | Entry Price | Self-host Cost | Notes |
|---------|-------|------------|----------------|-------|
| **VPSGaussianSplat** | Open source + SaaS tier | Free (self-host) | GPU compute only (~$5-20/scene) | No API query fees |
| **MultiSet** | SaaS | Free sandbox | N/A | Production: maps + area + API calls; custom SLAs for private |
| **8thWall** | Per-query + subscription | ~$200/mo | N/A | — |
| **Immersal** | Per m² | ~€1/m²/mo | N/A | — |
| **ARKit** | Free (iOS lock-in) | Free | N/A | Platform-locked |

### 7. Platform Support

| Feature | VPSGaussianSplat | MultiSet | 8thWall | Immersal | ARKit |
|---------|-----------------|----------|---------|----------|-------|
| iOS browser | ✅ | ❌ | ❌ | ❌ | ❌ |
| iOS native | ❌ | ✅ | ✅ | ✅ | ✅ |
| Android browser | ✅ | ❌ | ❌ | ❌ | ❌ |
| Android native | ❌ | ✅ | ✅ | ✅ | ❌ |
| Web (WebGL/WebXR) | ✅ Three.js | ✅ WebXR | ✅ | ❌ | ❌ |
| Unity | ✅ | ✅ | ✅ | ✅ | ❌ |
| Meta Quest | ❌ | ✅ SDK | ❌ | ❌ | ❌ |
| Meta Ray-Ban | ❌ | ✅ SDK | ❌ | ❌ | ❌ |

### 8. Multi-User / Real-Time

| Feature | VPSGaussianSplat | MultiSet | 8thWall | Immersal |
|---------|-----------------|----------|---------|----------|
| Multi-agent sync | ✅ WebSocket | ❌ | ❌ | ❌ |
| Shared anchors | ✅ REST API | ❌ | ✅ | ❌ |
| Live pose sharing | ✅ Real-time | ❌ | ❌ | ❌ |
| Multiplayer sample | ❌ | ✅ Unity sample (v1.12.0) | ❌ | ❌ |

---

## MultiSet Feature Timeline (Dec 2024 – June 2026)

| Version | Date | Key Features |
|---------|------|-------------|
| v1.1.0 | Dec 2024 | Map codes, raw mesh download, accuracy improvements |
| v1.2.0 | Dec 2024 | Custom localization animations, MapSet transforms |
| v1.3.0 | Jan 2025 | Unity SDK: simulation mode, download meshes, relocalization, occlusion |
| v1.4.0 | Jan 2025 | Third-party E57 scans, Unity navigation sample |
| v1.5.0 | Feb 2025 | Improved accuracy under challenging conditions, multi-frame localization |
| v1.5.2 | Mar 2025 | Email notifications, large map improvements, MapSet merge precision |
| v1.6.0 | Apr 2025 | *(data missing)* |
| v1.6.5 | Jun 2025 | *(data missing)* |
| v1.7.0 | Jul 2025 | *(data missing)* |
| v1.8.0 | Jul 2025 | **ModelSet** (object anchoring with textured meshes), WebXR ModelSet |
| v1.8.1 | Aug 2025 | Meta Quest SDK via UPM, confidence check in tracking, URP support |
| v1.9.0 | Sep 2025 | Unity mapping scene (LiDAR), continuous localization, Quest nav scene |
| v1.9.1 | Sep 2025 | Localization simulation in Unity, NavVis E57 support, E57 upload API |
| v1.9.2 | Oct 2025 | Matterpak processing, Meta Quest multi-frame localization |
| v1.9.3 | Nov 2025 | Xgrids E57 support, iPad UI, mesh gen improvements |
| v1.10.0 | Dec 2025 | **On-device localization iOS**, multi-object tracking, Faro support, analytics |
| v1.11.0 | Feb 2026 | **Native iOS/Android SDK**, glb objects (50MB, PBR/Draco), CORS, NPM WebXR |
| v1.11.1 | Mar 2026 | hintRadius/2D filtering, success heatmaps, Meta Ray-Ban SDK, manual MapSet |
| v1.12.0 | Apr 2026 | **Gaussian Splat → VPS** (Xgrids), hintFloorHeight, multiplayer Unity sample, Ray-Ban speed |
| v1.14.0 | May 2026 | **Map versioning**, VPS-powered MapSet merging, **360 scan beta**, on-device Android, E57 mesh improvements, faster API |
| v2.0.0 | Jun 2026 | **VPS Gen2** (better repetitive areas), 360-to-VPS GA, indoor/outdoor 360 modes, geometric + high-fidelity splat outputs |

---

## When to Choose What

**Choose VPSGaussianSplat when:**
- You need photorealistic AR (Gaussian splatting in-view, not just as import)
- You want to self-host for data privacy (hospitals, gov, enterprise, defense)
- You need indoor VPS with RGB video capture (no LiDAR required)
- You want an open, customizable pipeline you can debug and tune
- You need multi-user real-time spatial sync via WebSocket
- Budget is constrained (open source + self-host, no per-query fees)

**Choose MultiSet when:**
- You want the most mature commercial VPS platform (18 releases, 18 months)
- You need 360 camera or professional LiDAR scanner support (E57, Matterpak, Insta360)
- You need on-device localization for offline mobile AR
- You want managed cloud processing with analytics dashboards
- You're building for Meta Quest or Ray-Ban smart glasses
- You need professional features: map versioning, georeferencing, MapSets

**Choose 8thWall when:**
- You need WebAR with VPS (most mature web SDK)
- You're building outdoor AR experiences
- You're already in the Niantic ecosystem

**Choose Immersal when:**
- You need a mature SLAM-based VPS SDK
- You're building for mobile (iOS/Android) native apps
- Per-m² pricing works for your scale

**Choose Apple ARKit when:**
- You're iOS-only and want free (but locked-in) VPS
- You don't need cross-platform or web deployment

---

## Our Position

```
VPSGaussianSplat occupies the intersection of:
  ├── Photorealistic in-view (Gaussian Splatting) ← No competitor renders GSplat live
  ├── Open-source / Self-host ← MultiSet is enterprise on-prem only
  ├── Video-based capture (no LiDAR needed) ← MultiSet requires LiDAR or 360 cam
  └── Web + API-first ← MultiSet is SDK-first
```

**Elevator pitch:** *"The open-source infrastructure layer for photorealistic AR — self-hostable, indoor-capable, Gaussian Splatting–native VPS. Upload a phone video, get a 6DoF-localizable photorealistic scene."*
