# Self-evaluation — Psychiatry Wing (`8528a856`)

**What this is:** a measurement of the shipped localization path against COLMAP ground truth on
scene `8528a856-1b83-4ba3-aab0-4ede76aefb77`, run on the Windows PC on 2026‑11‑16.

**What this is not:** a held-out benchmark. The query frames come from the *same* capture that built
the map, so their descriptors are already in the FAISS index. Numbers here are an optimistic upper
bound on recall and a realistic read on precision. A defensible accuracy claim needs a second capture
session fed to `benchmark_localization.py` via a `vps.real_benchmark.v1` manifest.

## Method

```bash
python backend/scripts/evaluate_localization.py --scene-id 8528a856-... --num-frames 40
```

`evaluate_localization.py` calls `VPSService.localize()` once per sampled frame — the same code path
the API uses — and compares the returned pose with the pose COLMAP registered for that image
(camera centre `C = -Rᵀt`, rotation angle from the relative rotation matrix).

Acceptance thresholds: inliers ≥ 30, translation error ≤ 0.5 map units, rotation error ≤ 10°.

## Scene state

| Metric | Value |
|---|---|
| Extracted frames | 496 |
| COLMAP registered images | **333** (67%) |
| DB frames | 496 |
| Feature mode | ORB (index: `features/8528a856-.../features.faiss`) |
| Splat | `sparse_points_fallback.ply` (0.1 MB) — **no trained 3DGS** |
| Scene status | `READY` |

## Results

| Run | Sampled | Solved | Accepted | Success rate |
|---|---|---|---|---|
| seed 42, 12 frames | 12 | 3 | 1 | **8.3 %** |
| seed 42, 40 frames | 40 | 4 | 1 | **2.5 %** |

Error distributions over the frames that solved:

| Run | Translation error (median / p95 / max) | Rotation error (median / p95 / max) | Inliers (median) |
|---|---|---|---|
| 12 frames | 0.033 / 0.050 / 0.052 | 8.4° / 18.1° / 19.1° | 61 |
| 40 frames | 0.027 / 0.049 / 0.052 | 13.8° / 93.9° / 107.0° | 43 |

## Reading the numbers honestly

- **When it locks on, position is good**: 2–5 cm translation error, consistent with the project's
  published `0.036 m` figure. That claim describes *solved* frames, not the success rate.
- **It rarely locks on**: 1 of 12, and 1 of 40, frames passed all three thresholds. The
  `95 % success rate` in the README is **not supported** by this scene.
- **Rotation is the weak axis**: two solved frames landed at 94° and 107° rotation error — the position
  was close while the orientation was wrong, which for AR anchoring is a failure, not a near miss.
- **The failures are not "no matches"**: rejected frames had 400–536 raw matches but only 6–13
  geometrically consistent inliers. The matching stage proposes plenty of correspondences; they do not
  survive the ratio test + PnP. Likely causes, in order of suspicion: repetitive corridor texture
  (self-similar frames), a sparse 3D model, and no spatial hint supplied to the query.
- Only 67 % of frames registered in COLMAP, so a third of the capture has no ground truth to localize
  against — weakens both the map and this evaluation.

## Consequences for the plan

1. The `validation_checklist.md` claim and the README badge should be qualified to state *solved-frame*
   accuracy and *measured* success rate separately.
2. Before any accuracy claim is used commercially, run a **held-out** capture through
   `benchmark_localization.py` (needs the field capture that Prompt 11 describes).
3. Cheap experiments that could move success rate, in order:
   - supply `hint_position` (the API already supports it) and re-measure;
   - raise ORB features / try the hybrid SIFT fallback path on the rejected frames;
   - train 3DGS for this scene so the splat is real, and inspect whether the sparse model is the
     bottleneck (959-ish points is very sparse for a hospital corridor).
4. `backend/scripts/test_localization.py` is stale — it calls `FeatureMapper.extract_orb_features`,
   which no longer exists. Either delete it in favour of `evaluate_localization.py` or rewrite its
   matcher against `FeatureService`/`VPSService`.

## Reproduction

Reports (gitignored, on the PC): `backend/storage/debug/self_eval_8528a856.json`,
`self_eval_8528a856_40.json`. The index was rebuilt by the earlier `test_localization.py` run before
the fix; re-running `evaluate_localization.py` is enough to reproduce these figures.
