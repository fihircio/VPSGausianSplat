# MultiSet's GSplat Decision: Strategic Analysis

## The Question
MultiSet added Gaussian Splat import in v1.12.0 (Apr 2026) but **only as a VPS map source**, not as a live renderer. Why? They could render GSplat in-view like we do. What drove that choice?

---

## 1. Device Constraints (Hard Ceiling)

MultiSet supports platforms we don't: **Meta Quest, Meta Ray-Ban, on-device mobile** (iOS/Android native).

| Device | Can it render GSplat @ 30fps? |
|--------|-------------------------------|
| iPhone 15 Pro | ✅ Barely (metal buffer ~20-30fps at 720p) |
| Android mid-range | ❌ |
| Meta Quest 3 | ❌ (mobile XR2 gen2, \~15fps max) |
| Meta Ray-Ban | ❌ (no GPU, renders nothing locally) |
| WebXR (mobile browser) | ❌ |

They'd have to **exclude Quest, Ray-Ban, and most Android phones** from GSplat rendering. That's ~60% of their platform surface. MultiSet chose breadth-over-fidelity — a defensible enterprise play.

**Our approach**: We only target web browsers with Three.js. Lower platform burden lets us push visual fidelity further.

---

## 2. Input Diversity Creates Pipeline Bloat

MultiSet accepts **7+ capture methods**: LiDAR app, 360 cam (Insta360), E57 scanners (Leica/Matterport/NavVis/Faro/Xgrids), Matterpak, and GSplat import.

Each input needs to produce a VPS map. If they also rendered GSplat in-view, they'd need:
- A mesh rendering pipeline (for E57/LiDAR scans — can't GSplat those)
- A GSplat rendering pipeline (for video/GSplat sources)
- Device-specific optimizations × 2

**Pipeline complexity doubles** for what enterprise customers would consider a "nice-to-have" feature.

**Our constraint is our advantage**: Phone video only. Single input → single rendering pipeline. We can afford GSplat.

---

## 3. Cost: The Unit Economics Don't Work

Using your cost structure:

| Cost | Mesh rendering (MultiSet) | GSplat rendering (us) |
|-----|--------------------------|----------------------|
| **Processing per scene** | ~$2-5 (mesh gen) | ~$7-30 (COLMAP + GSplat training) |
| **Storage per scene** | ~$0.50/mo (mesh + features) | ~$2-5/mo (splat file is bigger) |
| **Runtime render cost** | ~$0 (trivial, device GPU) | ~$0.001-0.01/query (if server-side rendered) |
| **Client battery drain** | Negligible | ~2-3x more (GSplat is GPU-intensive) |

MultiSet's pricing is per-m² and per-API-call. If they rendered GSplat, their **COGS per query** would increase — eating margins on their current pricing model.

For us, GSplat rendering is our **differentiator**, so we accept the cost. For MultiSet, it would be a cost increase on a feature their enterprise customers aren't asking for.

---

## 4. Customer Fit: Who Needs Photorealism?

| Customer Segment | Needs | GSplat value |
|-----------------|-------|-------------|
| **Mall navigation** | Find store, show directions | Low — mesh is fine |
| **Factory maintenance** | Locate equipment, show schematics | Low — text + arrows |
| **Hospital wayfinding** | Guide to department | Medium — visual landmarks help |
| **Event/marketing AR** | Immersive brand experience | **High** — photorealism matters |
| **Real estate / digital twins** | Previsualize spaces | **High** — must look real |
| **AR gaming** | Blend real/virtual | **High** — immersion |

MultiSet targets the **top 3** (malls, factories, hospitals). We should target the **bottom 3** (events, real estate, immersive). Different customers = different rendering choices.

Their v2.0.0 addition of "high-fidelity splat outputs" is telling — they're **preparing** for GSplat rendering but haven't committed. It's a hedge.

---

## 5. Strategic Timing: GSplat Is Still Maturing

Gaussian Splatting is ~3 years old (July 2023). Its rendering pipeline for mobile/web:
- WebGL/WebGL2: ✅ Works (three.js-gaussian-splat, Luma)
- WebGPU: ✅ Better performance but only Chrome/Edge
- Mobile Safari: ⚠️ Metal path via WebGL, 15-25fps
- Mobile Chrome: ⚠️ Vulkan path, variable
- **Native mobile**: ❌ No mature SDK
- **Quest/XR**: ❌ No native runtime
- **Ray-Ban**: ❌ Impossible

MultiSet launched v1.0 in late 2024 — GSplat was only 1 year old. Committing to it then would have been high risk. Their strategy: **wait and watch** → add as import in v1.12.0 → add "high-fidelity outputs" in v2.0.0 → likely add GSplat viewer in v2.x or v3.x once the ecosystem matures.

They're riding the S-curve, not betting on it early.

---

## 6. Competitive Dynamics: They're Following Us, Not Vice Versa

This is the key insight: **MultiSet added GSplat import in April 2026. Our project started April 2026.**

Timeline:
| Date | Us | MultiSet |
|------|----|----------|
| Jul 2023 | — | — | GSplat paper published |
| Late 2024 | — | v1.x launch (mesh VPS) |
| Apr 2026 | **Project start** (GSplat-native VPS) | — |
| Apr 2026 | — | **v1.12.0: GSplat import added** |
| Jun 2026 | MVP live, ~4cm accuracy | v2.0.0: high-fidelity splat outputs |

They added GSplat support **the same month we launched**. Coincidence? Possibly. But it suggests:
- They saw GSplat-native VPS as a competitive threat
- Adding GSplat import was a defensive move (low cost, high optionality)
- "High-fidelity splat outputs" in v2.0.0 is their next step toward rendering

---

## Summary: Why They Didn't Go All-In

| Factor | Weight | Verdict |
|--------|--------|---------|
| Device constraints | 🔴 Critical | Quest/Ray-Ban/Android can't render GSplat |
| Pipeline complexity | 🟡 Medium | 7 inputs × 2 renderers = too much |
| Cost per query | 🟡 Medium | Would eat into enterprise margins |
| Customer demand | 🔴 Critical | Enterprise doesn't need photorealism |
| Tech maturity | 🟡 Medium | GSplat was too new in 2024 |
| Competitive hedge | 🟢 Minor | They're following, not leading |

**Their bet**: Enterprise reliability × platform breadth beats visual fidelity.

**Our bet**: Visual fidelity × developer experience beats enterprise features.

Both are defensible. The question is which market is larger and which we can capture first. Our cost structure is lower (no Quest/Ray-Ban support, simpler pipeline), and our differentiation is sharper (photorealism). Their advantage is breadth.

**The trap to avoid**: Don't copy MultiSet's feature set. We can't out-enterprise the enterprise player. We win by being the **best GSplat-native VPS**, not by being "MultiSet but cheaper."
