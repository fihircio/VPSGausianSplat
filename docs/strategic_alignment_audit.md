# Strategic Alignment Audit: Where We Stand vs The Plan

## Summary

**Are we on the right track?** Yes, mostly — our differentiators are strong, but there's a dangerous gap in core VPS table-stakes features.

---

## What We Got Right (Our Differentiators Are Real)

| Our Advantage | Status | Evidence |
|---|---|---|
| GSplat rendering live in-view | ✅ **GREEN** | Three.js renderer, tile streaming, octree culling — all working in `frontend/app/scenes/[id]/viewer/page.tsx` |
| Video-based capture (no LiDAR) | ✅ **GREEN** | Full upload + frame extraction pipeline in `backend/api/routes_scene.py:86-167` |
| In-app recording in navigatus | ✅ **GREEN** | Resolution selector, countdown, upload with progress — all in `navigatus/src/App.tsx:1177-1419` |
| WebSocket multi-agent sync | ✅ **GREEN** | ConnectionManager + broadcast + persistence in `backend/services/sync_service.py:1-126` |
| Open source self-host | ✅ **GREEN** | Full stack available, docker-compose for infra, pluggable storage (local/S3/Azure) |
| Shared anchors API | ✅ **GREEN** | CRUD + GLB spawning in `backend/api/routes_scene.py:261-334` + `frontend/lib/AnchorManager.ts` |

These are the features MultiSet **cannot easily copy** (their pipeline requires LiDAR, they don't do live GSplat, they don't have WebSocket sync, their "self-host" is enterprise-only contact-sales).

---

## What We Got Wrong (Phase 1 Should Have Started)

The execution matrix says Phase 1 = 9 days for multi-frame VPS + hints. We've done **zero** of this work.

| Critical Gap | Impact | Effort |
|---|---|---|
| **Multi-frame VPS** | MultiSet has it. Without it, our single-frame localization fails in repetitive spaces (corridors, basements). This is their Gen2 feature — and it exists because it matters. | ~5 days |
| **hintPosition + hintRadius** | Every localization searches the entire FAISS index. On a 10,000-frame scene, this is slow and brittle. No spatial prior = failed matches in large spaces. | ~1 day |
| **hintFloorHeight** | Multi-floor hospitals/campuses are our target market. Without this, localization can match a photo to the wrong floor. | ~1 day |
| **GeoHint** | MultiSet says this speeds up localization 15%. Easy win with GPS from phone. | ~1 day |
| **Image resolution limit** | No resize on capture. Navigatus sends full camera resolution (~4K on modern phones) to FAISS. This is wasteful and slow. | ~1 day |

**Phase 1 total**: ~9 days. **Status**: 0/9 days done.

This is the gap that matters most. These aren't "enterprise extras" — they're fundamental VPS quality features.

---

## What We're Over-Invested In

| Area | Status | Verdict |
|---|---|---|
| **Commercial docs** (7 documents in `docs/commercial/`) | ✅ DONE | Useful, but over-indexing for pre-revenue. We have pricing decks but no billing system. |
| **Landing page copy** | ✅ DONE | Looks professional but the VPS pipeline needs hardening before we can sell. |
| **MultiSet deep-dive analysis** (3 documents) | ✅ DONE | Good competitive intel, but now we need to _act_ on it. |

These are easy to write when you're avoiding hard engineering work. The docs are good — but they don't fix the VPS gaps.

---

## What's Tracking Correctly

| Area | Status | Execution Matrix Alignment |
|---|---|---|
| Skipping E57/LiDAR/360 input | ✅ Correct | "Our advantage: RGB video only" — aligned |
| Skipping Object Tracking | ✅ Correct | "Separate product, not VPS" — aligned |
| Skipping Quest SDK | ✅ Correct | "Revisit after Unity SDK + revenue" — aligned |
| Skipping native iOS/Android SDK | ⚠️ Partially correct | PWA covers most, but we should revisit if enterprise customers demand it |
| Documentation quality | ✅ Strong | 18+ docs, all well-written — aligned with "developer-centric" positioning |
| Unity SDK (VpsClient + converter) | ✅ Core exists | Missing sample scenes + NavMesh — this is Phase 2 work |

---

## The Dangerous Gap: Our Pitch Exceeds Our Reality

Our README says: *"~4cm accuracy, sub-decimeter VPS"* — but this is on a single benchmark scene (KLCC). Without multi-frame and spatial hints, real-world accuracy in large or repetitive environments will be significantly worse.

MultiSet's docs transparently report: *"6cm median, drift <1cm @10m, <6cm @100m"* with explicit conditions. We report *"~4cm"* with no conditions. This is the "accuracy overblown" risk the SWOT identified.

**If a pilot customer tests us in a hospital corridor (repetitive, long, low texture), our single-frame VPS will fail more often than MultiSet's multi-frame + hintPosition + hintFloorHeight combo.**

---

## Recommendation: Immediate Next 2 Weeks

Stop writing docs. Start shipping Phase 1.

| Day | Task |
|-----|------|
| 1-2 | **hintPosition + hintRadius**: Add optional params to `/vps/localize`, filter FAISS results by 3D distance |
| 3 | **hintFloorHeight**: Same as above, Y-axis band filter |
| 4 | **GeoHint**: Accept GPS coords, convert to approximate scene position, use as hintPosition |
| 5 | **Client-side resize**: cap capture resolution to 1280px in navigatus + add resize middleware to backend |
| 6-10 | **Multi-frame VPS**: New endpoint `/vps/localize/multi` accepting 4-6 images, average/refine poses |

**After Phase 1**, the VPS pipeline is solid. Then Phase 2 (Unity sample scenes + JWT auth) prepares us for real demos.

---

## Bottom Line

**Strengths (keep doing):**
- GSplat rendering as our core visual differentiator ✅
- Multi-agent sync (no competitor does this) ✅
- Video-based capture with in-app recording ✅
- Open source + comprehensive docs ✅

**Weaknesses (fix now):**
- No multi-frame VPS — biggest accuracy gap
- No spatial hints — limits real-world reliability in large/repetitive spaces
- No image resolution limits — wasteful and slow
- Docs are over-invested relative to engineering

**The strategy is sound** — depth over breadth, GSplat-native, video-based, web-first. But Phase 1 features aren't "enterprise extras" — they're _table stakes_ for a VPS that works outside the demo scene. We can't claim ~4cm accuracy without multi-frame + hints to back it up in real conditions.
