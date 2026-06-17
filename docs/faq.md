# Developer FAQ: VPSGaussianSplat

## General

### What is VPSGaussianSplat?
A Visual Positioning System that uses Gaussian Splatting for photorealistic scene representation. Upload a phone video, get a 6DoF-localizable AR scene with ~4cm accuracy.

### How is it different from ARKit / ARCore?
Those are device-local SLAM systems tied to specific hardware. VPSGaussianSplat is server-based VPS: any phone camera can localize against a pre-mapped scene, regardless of platform or LiDAR.

### Is it really open source?
Yes. The core backend, frontend, and navigatus app are MIT-licensed and available on GitHub. No proprietary SDKs or black-box models.

---

## Pipeline

### What happens when I upload a video?

1. **Frame extraction** — ffmpeg extracts keyframes (default: every 3rd frame)
2. **COLMAP SfM** — sparse reconstruction → camera poses + 3D point cloud
3. **Feature indexing** — ORB/SIFT descriptors extracted and indexed via FAISS
4. **Gaussian Splatting** — (optional, for visualization) train 3D Gaussians from COLMAP output
5. **Ready** — scene is now localizable via the VPS endpoint

### How long does processing take?

| Video length | Frames | COLMAP | Feature index | GSplat | Total |
|-------------|--------|--------|--------------|--------|-------|
| 30s @ 30fps | ~300 | 2-5 min | 30s | 5-10 min | 8-16 min |
| 2min @ 30fps | ~1200 | 10-30 min | 2-5 min | 30-60 min | 45-95 min |

Times depend on GPU (CUDA vs CPU), video quality, and scene complexity.

### Can I use pre-recorded video?
Yes. Any MP4/MOV from any camera works. No special capture hardware needed.

### What features/extractors are supported?
- ORB (OpenCV, fast, good for real-time)
- SIFT (OpenCV, more robust, slower)
- SuperPoint (planned, better for low-texture)
- LightGlue (planned, learned matcher)

You can swap extractors per scene via the API.

---

## Accuracy

### How accurate is localization?
~4cm average positional error (0.036m) based on KLCC benchmark with ORB + 3D-to-2D PnP RANSAC. Inlier ratio typically 0.5-0.8.

### What affects accuracy?
- **Scene coverage** — 2 complete loops clockwise + counter-clockwise
- **Lighting** — consistent lighting between mapping and query
- **Texture** — more visual features = more correspondences
- **Repetitive patterns** — long corridors, glass walls reduce accuracy
- **Dynamic objects** — people/furniture moved between map and query

### Can I trust the confidence score?
Yes. `confidence` = inlier ratio from PnP RANSAC. ≥0.5 is "locked," ≥0.3 is "weak," <0.3 is effectively a failure.

---

## Deployment

### Can I run this on my own server?
Yes. Backend runs on any Linux/Windows/Mac with Docker or bare metal. Minimum requirements:
- 4 CPU cores
- 8GB RAM
- NVIDIA GPU (optional, speeds up COLMAP + GSplat)
- 20GB free disk per scene

### Can I deploy to the cloud?
The Docker Compose setup works on any cloud VM. We also plan a managed SaaS tier.

### Can I use this offline?
The backend must be reachable. If you self-host on a local network with no internet, everything works. The mobile app (PWA) also works offline for basic AR — only VPS localization needs the network.

### Do I need to expose my server to the internet?
No. For a hospital/enterprise deployment, run the backend on your internal network. The PWA and Unity SDK connect over LAN or VPN.

---

## Mobile

### Does it work on iOS?
Yes — navigatus is a PWA that works on Safari (iOS 15+). No App Store needed.

### Does it work on Android?
Yes — Chrome on Android. Camera access, motion sensors, and WebGL all work.

### Do I need LiDAR?
No. VPSGaussianSplat works with any standard RGB camera. LiDAR is not used.

### How does recording work?
Navigatus has a built-in recorder: MediaRecorder API captures VP9/VP8 WebM, uploads directly to the backend via XHR with progress tracking. Includes countdown, resolution selector, and live file-size estimate.

---

## Unity SDK

### What platforms does the Unity SDK support?
iOS, Android, Windows, macOS, and WebGL (pending).

### What's the API surface?
```csharp
var client = new VpsClient(apiBaseUrl, apiKey);
VpsPose pose = await client.LocalizeAsync(sceneId, texture);
```

That's it. One method. Position and rotation come back as Vector3/Quaternion.

### Can I place AR objects relative to VPS poses?
Yes. Anchor positions are in scene coordinates. Transform any VPS pose into world space and place objects accordingly. Shared anchors work via the backend API.

---

## API

### How do I authenticate?
All mutating endpoints require `X-API-Key` header. Set via `VPS_API_KEY` environment variable on the backend, and `NEXT_PUBLIC_API_KEY` on the frontend.

### Is there rate limiting?
Not yet built-in (planned for v0.3). For now, be reasonable — don't spam `/localize` at 60Hz.

### What format are poses in?
- `position`: [x, y, z] in meters, scene coordinate system
- `rotation`: [w, x, y, z] quaternion
- `confidence`: float 0-1 (inlier ratio)
- `inliers`: integer count of PnP RANSAC inliers

### Can I use WebSocket for real-time poses?
Yes — the backend exposes a WebSocket endpoint for streaming localization. Useful for multi-user AR sessions and live pose sharing.

---

## Comparison

### How does this compare to Google VPS / Niantic VPS?
| | Ours | Google VPS | Niantic VPS |
|---|---|---|---|
| Coverage | Your space | Google-mapped areas | Niantic-mapped areas |
| Indoor | ✅ | ❌ (limited) | ❌ |
| Self-host | ✅ | ❌ | ❌ |
| Privacy | Full control | Google servers | Niantic servers |
| Cost | Free (open source) | Pay-per-query | Subscription |
| Visual quality | Gaussian splatting | Standard mesh | Standard mesh |

### How does this compare to Meshroom / Reality Capture?
Those are photogrammetry tools (mesh + texture). VPSGaussianSplat adds VPS localization on top — the ability to query a live camera image and get back a 6DoF pose. If you only need 3D reconstruction, use Meshroom. If you need to *localize in* that reconstruction, use VPSGaussianSplat.

---

## Troubleshooting

### Localization always returns low confidence (<0.3)
- Query image is too different from the mapping video (different lighting, season, angle)
- Scene wasn't captured thoroughly (need 2 loops)
- Too few features in the scene (glass walls, white corridors)
- Try SIFT instead of ORB

### COLMAP fails with "no matches"
- Video is too dark or blurry
- Scene has no visual texture (blank white walls, featureless floor)
- Increase frame extraction rate (--extract-every-nth 2)

### Processing stuck on "PROCESSING"
Check the backend logs. Most common issue: disk space. COLMAP and splatting need ~20GB+ free per scene.

### Can I use a CPU-only machine?
Yes — everything works on CPU, just slower. COLMAP's sequential matcher is the bottleneck. Expect 10-20x slower than GPU.

### The frontend shows blank page
Check that `NEXT_PUBLIC_API_BASE_URL` and `NEXT_PUBLIC_API_KEY` are set in `.env.local`. Also check browser console for CORS errors.
