# Competitive Comparison: VPSGaussianSplat vs Alternatives

## Overview

| | VPSGaussianSplat | MultiSet.ai | 8thWall (Niantic) | Immersal (Hexagon) | Apple ARKit |
|---|---|---|---|---|---|
| **Core tech** | Gaussian Splatting + SfM + FAISS | Neural VPS + mesh | Visual positioning + mesh | SLAM + mesh | ARWorldMap + mesh |
| **Visual quality** | ★★★★★ Photorealistic | ★★★★ Good | ★★★ Standard mesh | ★★★ Standard mesh | ★★★ Standard mesh |
| **VPS accuracy** | ~4cm avg (0.036m) | Claims <10cm | ~10-50cm | ~10-30cm | ~10-50cm |
| **Indoor support** | ✅ Built for it | ✅ | ❌ GPS-focused | ✅ | ❌ Limited |
| **Self-hostable** | ✅ Open source | ❌ Cloud-only | ❌ | ❌ | ❌ |
| **Open API** | ✅ REST + WebSocket | ✅ REST | ✅ REST | ✅ REST | ❌ iOS only |

---

## Detailed Feature Comparison

### 1. Rendering & Visual Quality

**VPSGaussianSplat** uses Gaussian Splatting — photorealistic novel view synthesis from sparse point clouds. This means:
- Real-time rendering of captured spaces with photographic quality
- No mesh simplification artifacts
- Orders of magnitude smaller than NeRF for equivalent quality

**Competitors** use mesh-based or point-cloud rendering. 8thWall and Immersal render textured meshes (lower fidelity). MultiSet uses neural rendering but doesn't match Gaussian splatting quality.

### 2. VPS Engine

**VPSGaussianSplat** pipeline:
1. ORB/SIFT features extracted from query image
2. FAISS nearest-neighbor retrieval against scene feature index
3. Lowe's ratio test → PnP RANSAC → 6DoF pose
4. Confidence scoring based on inlier ratio

**MultiSet** uses a proprietary neural VPS. **8thWall** uses Niantic's Visual Positioning System (VPS). **Immersal** uses visual-inertial SLAM. All are closed-source black boxes.

**Key advantage:** Open pipeline means you can swap feature extractors (ORB → SIFT → SuperPoint → LightGlue), tune parameters per scene type, and debug failures.

### 3. Deployment Model

| | Self-host | Cloud SaaS | Mobile SDK | Web SDK | Unity SDK |
|---|---|---|---|---|---|
| **VPSGaussianSplat** | ✅ | ✅ (planned) | ✅ (PWA) | ✅ (Three.js) | ✅ |
| **MultiSet** | ❌ | ✅ | ✅ | ❌ | ❌ |
| **8thWall** | ❌ | ✅ | ✅ | ✅ | ✅ |
| **Immersal** | ❌ | ✅ | ✅ | ❌ | ✅ |
| **Apple ARKit** | ❌ | ❌ | ❌ (iOS only) | ❌ | ❌ |

### 4. Pricing

| Product | Model | Entry Price | Self-host Cost |
|---------|-------|------------|----------------|
| **VPSGaussianSplat** | Open source + SaaS tiers | Free (self-host) | GPU compute only (~$5-20/scene) |
| **MultiSet** | Enterprise SaaS | ~$8k+/pilot | N/A |
| **8thWall** | Per-query + subscription | ~$200/mo basic | N/A |
| **Immersal** | Per m² | ~€1/m²/mo | N/A |
| **Apple ARKit** | Free (iOS lock-in) | Free | N/A |

### 5. Platform Support

| Feature | VPSGaussianSplat | MultiSet | 8thWall | Immersal | ARKit |
|---------|-----------------|----------|---------|----------|-------|
| iOS | ✅ (browser) | ✅ | ✅ | ✅ | ✅ (native) |
| Android | ✅ (browser) | ✅ | ✅ | ✅ | ❌ |
| Web | ✅ (Three.js) | ❌ | ✅ | ❌ | ❌ |
| Unity | ✅ | ❌ | ✅ | ✅ | ❌ |
| Custom | ✅ (REST API) | ✅ (REST API) | ✅ (REST API) | ✅ (REST API) | ❌ |

### 6. Multi-User / Real-Time

| Feature | VPSGaussianSplat | MultiSet | 8thWall | Immersal |
|---------|-----------------|----------|---------|----------|
| Multi-agent sync | ✅ WebSocket | ❌ | ❌ | ❌ |
| Shared anchors | ✅ REST API | ❌ | ✅ | ❌ |
| Live pose sharing | ✅ Real-time | ❌ | ❌ | ❌ |

---

## When to Choose What

**Choose VPSGaussianSplat when:**
- You need photorealistic AR (Gaussian splatting quality)
- You want to self-host for data privacy (hospitals, gov, enterprise)
- You need indoor VPS (hospitals, malls, campuses)
- You want an open, customizable pipeline
- You need multi-user real-time spatial sync
- Budget is constrained (open source + self-host)

**Choose MultiSet when:**
- You want a fully managed enterprise VPS solution
- You're willing to pay for cloud-only deployment
- You don't need self-hosting or data residency

**Choose 8thWall when:**
- You need WebAR with VPS (they have the most mature web SDK)
- You're building outdoor AR experiences
- You're already in the Niantic ecosystem

**Choose Immersal when:**
- You need a mature SLAM-based VPS SDK
- You're building for mobile (iOS/Android) native
- Per-m² pricing works for your scale

**Choose Apple ARKit when:**
- You're iOS-only and want free (but locked-in) VPS
- You don't need cross-platform or web deployment

---

## Our Position

```
VPSGaussianSplat occupies the intersection of:
  ├── Photorealistic (Gaussian Splatting) ← No competitor is here
  ├── Open-source / Self-host ← MultiSet is opposite
  ├── Indoor-first ← 8thWall/ARKit are outdoor-first
  └── Web + API-first ← Immersal/ARKit are SDK-locked
```

**Elevator pitch:** *"The open-source infrastructure layer for photorealistic AR — self-hostable, indoor-capable, Gaussian Splatting–native VPS."*
