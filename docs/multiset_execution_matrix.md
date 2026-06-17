# MultiSet Feature Execution Matrix

Every MultiSet feature mapped to our status, effort estimate, and build/skip/partner recommendation.

---

## Tier 1: Core VPS Pipeline

| Feature | MultiSet | We Have | Effort | Verdict |
|---------|----------|---------|--------|---------|
| **Single-frame VPS** | ✅ `/vps/map/query` (image base64) | ✅ `/vps/localize` (image file) | Done | **Keep** |
| **Multi-frame VPS** (4-6 images→pose) | ✅ `/vps/map/multi-image-query` | ❌ | **Medium (3-5d)** | **Build** — improves accuracy in repetitive spaces |
| **Confidence scoring** | ✅ Multi-metric (v1.12.0) | ✅ Inlier ratio | Done | **Keep** — simpler is fine |
| **hintPosition** (search radius) | ✅ `[x,y,z]` + hintRadius (1-100m) | ❌ | **Small (1d)** | **Build** — critical for large scenes |
| **hintFloorHeight** (Y-band filter) | ✅ `[y_min, y_max]` | ❌ | **Small (1d)** | **Build** — multi-floor req |
| **hintMapCodes** (subset search in MapSet) | ✅ Map code array | ❌ | **Small (1d)** | **Skip** — no MapSet yet |
| **GeoHint** (GPS→VPS speedup) | ✅ GPS coords narrow search | ❌ | **Small (1d)** | **Build** — 15% faster, easy |
| **GeoPose output** (WGS84) | ✅ | ❌ | **Medium (3d)** | **Skip** — niche, few customers |
| **Max image resolution** | 1280px limit | No limit | — | **Add** client-side resize to 1280px |
| **LHS/RHS coordinate conversion** | ✅ Auto | ❌ | **Small (1d)** | **Build** — Unity SDK needs this |

**Tier 1 total effort:** ~8-10 days

---

## Tier 2: Capture & Input

| Feature | MultiSet | We Have | Effort | Verdict |
|---------|----------|---------|--------|---------|
| **Phone video → VPS** | ❌ (LiDAR required) | ✅ (RGB only) | Done | **Our advantage** — no LiDAR needed |
| **In-app recording** | ❌ (separate app) | ✅ navigatus PWA | Done | **Our advantage** |
| **LiDAR phone scanning** | ✅ Mapping App + Unity SDK | ❌ | **High (2-3wk)** | **Skip** — against our positioning |
| **360 video capture** (Insta360) | ✅ Beta (v1.14.0) → GA (v2.0.0) | ❌ | **High (2wk)** | **Skip** — partner with Xgrids instead |
| **E57 scanner import** | ✅ Matterport, Leica, NavVis, Faro, Xgrids | ❌ | **High (3-4wk)** | **Partner** — process externally, import features |
| **Matterpak import** | ✅ | ❌ | **Medium (1wk)** | **Skip** — niche format |
| **GSplat import** | ✅ (upload .ply + poses.json) | ✅ Native | Done | **Our advantage** |
| **Raw mesh export** (.glb) | ✅ | ✅ (COLMAP output) | Done | **Keep** — add direct .glb download endpoint |

**Tier 2 total effort:** ~2-3 days (only phone video improvements, skip rest)

---

## Tier 3: Map Management

| Feature | MultiSet | We Have | Effort | Verdict |
|---------|----------|---------|--------|---------|
| **Map versioning** (re-scan→same frame) | ✅ VPS-powered (v1.14.0) | ❌ | **High (3-4wk)** | **Skip** — enterprise feature, v2.0 |
| **MapSet / map stitching** | ✅ Overlap + manual + VPS | ❌ | **High (4-6wk)** | **Skip** — rebuild pipeline, v2.0 |
| **Map archiving** | ✅ (v1.10.0) | ❌ | **Small (1d)** | **Build** — soft delete for scenes |
| **Analytics dashboard** | ✅ Query heatmaps, success rates (v1.11.1) | ❌ | **Medium (1-2wk)** | **Build** — basic version for debug |
| **CORS configuration in UI** | ✅ (v1.11.0) | ❌ | **Small (1d)** | **Build** — portal security |
| **Multi-tenant auth** | ✅ JWT + scopes (Query/Write/Delete) | ⚠️ API key only | **Medium (1wk)** | **Build** — replace API key with JWT |
| **3D viewer / point cloud** | ✅ Portal | ✅ Portal | Done | **Keep** — improve splat viewer |

**Tier 3 total effort:** ~2-3 weeks

---

## Tier 4: Platform & SDK Support

| Feature | MultiSet | We Have | Effort | Verdict |
|---------|----------|---------|--------|---------|
| **Unity SDK** (loc, mapping, nav, tracking) | ✅ Full SDK | ⚠️ Partial (VpsClient only) | **High (4-6wk)** | **Build** — expand Unity SDK with localization scene |
| **iOS Native SDK** | ✅ Swift native (v1.11.0) | ❌ | **High (4wk)** | **Skip** — PWA covers iOS |
| **Android Native SDK** | ✅ Kotlin native (v1.11.0) | ❌ | **High (4wk)** | **Skip** — PWA covers Android |
| **WebXR SDK** (NPM) | ✅ `@multisetai/vps` (v1.11.0) | ⚠️ Three.js only | **Medium (1-2wk)** | **Build** — NPM package with GSplat renderer |
| **Meta Quest SDK** | ✅ (v1.9.0+) | ❌ | **High (4-6wk)** | **Skip** — revisit after revenue |
| **Meta Ray-Ban SDK** | ✅ (v1.11.1) | ❌ | **Small (1wk)** | **Build** — it's just REST API + sample code |
| **ROS 2 SDK** | ✅ | ❌ | **Medium (2wk)** | **Skip** — industrial niche |

> **Ray-Ban insight**: It doesn't render anything locally. It's a camera that sends images to the cloud VPS and receives poses. We already have the REST API. "Build" = write a sample app that uses our `/vps/localize` endpoint from the Ray-Ban camera stream. This is ~$1k in glasses + 1 week of work.

**Tier 4 total effort:** ~2-3 weeks (Unity SDK + WebXR NPM + Ray-Ban sample)

---

## Tier 5: Object Tracking

| Feature | MultiSet | We Have | Effort | Verdict |
|---------|----------|---------|--------|---------|
| **GLB upload → cloud processing** | ✅ (v1.8.0, renamed v1.11.0) | ❌ | **High (4-6wk)** | **Skip** — separate product |
| **On-device tracking** | ✅ iOS/Android native (v1.14.0) | ❌ | **High (8wk+)** | **Skip** — needs native SDK |
| **Multi-object tracking** | ✅ (v1.10.0) | ❌ | **High (12wk+)** | **Skip** |
| **Object tracking from Unity** | ✅ | ❌ | **High (4wk)** | **Skip** |

> **Object Tracking is a distinct product**, not a VPS feature. MultiSet only added it because their enterprise customers asked for it (anchoring AR to specific equipment/machinery). We should not build this. If needed, we can partner with a 3D model tracking library.

**Tier 5 total effort:** Skip entirely

---

## Tier 6: Navigation & Multi-User

| Feature | MultiSet | We Have | Effort | Verdict |
|---------|----------|---------|--------|---------|
| **Unity NavMesh navigation** | ✅ | ❌ | **Medium (2wk)** | **Build** — Unity SDK with pathfinding |
| **Multi-agent sync** | ❌ (only multiplayer sample in Unity) | ✅ WebSocket | Done | **Our advantage** |
| **Shared anchors** | ❌ | ✅ REST API | Done | **Our advantage** |
| **Multi-layer (floor) navigation** | ✅ | ❌ | **Medium (2wk)** | **Build** — hintFloorHeight + level switching |
| **Simulation mode** (test in editor) | ✅ (v1.9.1) | ❌ | **Medium (1wk)** | **Build** — useful for Unity SDK |

**Tier 6 total effort:** ~5 weeks (but we lead in multi-agent)

---

## Tier 7: Business & Deployment

| Feature | MultiSet | We Have | Effort | Verdict |
|---------|----------|---------|--------|---------|
| **Self-host / open source** | ❌ (enterprise on-prem only) | ✅ | Done | **Our advantage** |
| **Cloud SaaS** | ✅ | ❌ | **Medium (2wk)** | **Build** — after multi-tenant JWT |
| **On-prem (private VPC)** | ✅ Enterprise | ✅ (self-host) | Done | **Our advantage** |
| **Fully offline (air-gapped)** | ✅ Enterprise | ✅ (self-host) | Done | **Our advantage** |
| **Sandbox tier (free)** | ✅ | ✅ (self-host) | Done | **Keep** |
| **Team management** | ✅ Portal | ❌ | **Medium (1-2wk)** | **Build** — v0.3 |
| **Billing / metering** | ✅ Maps + area + API calls | ❌ | **High (4wk)** | **Build** — after pilots close |
| **Usage analytics** | ✅ | ❌ | **Medium (1wk)** | **Build** — basic tracking |

**Tier 7 total effort:** ~4-6 weeks (spread across v0.2→v0.4)

---

## Summary: Where to Spend Our Time

### Phase 1 (Now — 2 weeks): Fast Parity Wins
| Priority | Feature | Days | Why |
|----------|---------|------|-----|
| 🥇 | Multi-frame VPS (4-6 images) | 5 | Big accuracy improvement, visible in demos |
| 🥇 | hintPosition + hintRadius | 1 | Unlocks large scenes, easy win |
| 🥇 | hintFloorHeight | 1 | Multi-floor scenes, easy win |
| 🥇 | GeoHint (GPS→VPS speedup) | 1 | Professional feature, easy win |
| 🥇 | LHS/RHS coordinate conversion | 1 | Unity SDK compatibility |

**Phase 1 cost:** ~9 days. **Result:** VPS parity on core API.

### Phase 2 (Weeks 3-4): SDK & Portal
| Priority | Feature | Days | Why |
|----------|---------|------|-----|
| 🥇 | Unity SDK expansion (localization scene) | 10 | Unlocks Quest/visionOS/enterprise |
| 🥇 | JWT multi-tenant auth | 5 | Replaces API key, enables teams |
| 🥈 | WebXR NPM package | 5 | Developer onboarding funnel |
| 🥈 | CORS UI + analytics | 5 | Portal professionalism |

**Phase 2 cost:** ~25 days. **Result:** Professional platform.

### Phase 3 (Weeks 5-8): Navigation & Scale
| Priority | Feature | Days | Why |
|----------|---------|------|-----|
| 🥇 | Unity NavMesh navigation | 10 | Indoor wayfinding use case |
| 🥇 | Multi-floor scene support | 5 | Hospital/campus requirement |
| 🥈 | Billing system | 20 | Revenue enablement |
| 🥈 | Meta Ray-Ban sample app | 5 | Marketing + wearables play |

**Phase 3 cost:** ~40 days. **Result:** Revenue-ready.

### Skip Entirely
| Feature | Reason |
|---------|--------|
| E57 scanner import | Partner with scanning companies instead |
| 360 video capture | Doesn't fit our RGB-video pipeline |
| Object Tracking | Separate product, not VPS |
| Meta Quest SDK | Too early, revisit after Unity SDK + revenue |
| MapSet / Map Stitching | Restructure pipeline, massive effort |
| Map Versioning | Enterprise luxury, revisit v2.0 |
| iOS/Android Native SDKs | PWA covers 95% of use cases |
| ROS 2 SDK | Industrial niche, no demand yet |

---

## Our Build Strategy: Not "Better MultiSet" but "Different MultiSet"

MultiSet built **breadth** (7 input types, 5 platforms, 18 releases). We should build **depth**:

| They do | We do |
|---------|-------|
| 7 ways to get data in | 1 way: phone video |
| Mesh rendering on all platforms | GSplat rendering on web + Unity |
| SDK wrappers for every device | REST API + 2 good SDKs (Unity, WebXR) |
| On-device VPS (native iOS/Android) | Cloud VPS via REST + PWA |
| Object Tracking (separate feature) | Shared anchors + multi-agent sync |
| Enterprise on-prem ($$$) | Open source self-host (free) |

**The goal:** Be the best GSplat-native VPS for developers who want to build photorealistic AR experiences with minimal friction. Not be "MultiSet but cheaper."
