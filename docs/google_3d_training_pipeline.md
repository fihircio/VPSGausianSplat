# Google 3D Training Pipeline Plan

## Position

Assumption: we have written permission to use Google Maps / Google Photorealistic 3D data for training, validation, derived datasets, and commercial model development.

This pipeline should use Google 3D as a synthetic geospatial data source for pretraining, evaluation, and outdoor bootstrapping. It should not replace real device capture for production VPS, because rendered 3D tiles do not reproduce real mobile camera behavior, motion blur, rolling shutter, crowds, weather, storefront changes, or indoor/outdoor transition issues.

Best use:

- Generate image and pose pairs at scale.
- Pretrain retrieval and feature-matching models.
- Build outdoor geospatial benchmark scenes.
- Test coordinate transforms, map tiling, and scene partitioning.
- Seed outdoor VPS demos before customer scans are available.

Do not use it as the only production truth source for paid deployments.

## Permission Record

Before any ingestion job runs, store the permission scope in an internal record:

```json
{
  "provider": "google",
  "source": "photorealistic_3d_tiles",
  "allowed_uses": ["train", "fine_tune", "benchmark", "evaluate", "commercial_model"],
  "allowed_storage": ["raw_tiles", "decoded_mesh", "rendered_rgb", "depth", "poses", "features"],
  "derived_model_commercialization": true,
  "retention_days": null,
  "document_uri": "internal_contract_or_permission_reference"
}
```

If any of these fields are unknown, mark the dataset as `internal_research_only` until clarified.

## Architecture

```text
Google 3D Tiles API
        |
        v
AOI tile traversal
        |
        v
Tile metadata + GLB/B3DM cache
        |
        v
ENU scene builder
        |
        v
Synthetic camera trajectory generator
        |
        v
Headless renderer
        |
        v
RGB / depth / normal / pose dataset
        |
        v
Feature extraction + VPS benchmark
        |
        v
Model training / regression reports
```

## Data Model

Minimum new domain objects:

- `data_permissions`: provider, source, allowed uses, retention, commercialization rights.
- `aois`: polygon, origin WGS84, origin ECEF, local ENU frame, market, priority.
- `source_tiles`: tile id, provider, tileset URI, bounding volume, transform, geometric error.
- `mesh_assets`: decoded GLB/B3DM path, texture references, checksum, LOD.
- `render_runs`: renderer version, camera policy, augmentation policy.
- `synthetic_frames`: RGB/depth/normal paths, intrinsics, extrinsics in ENU and ECEF, tile coverage.
- `feature_runs`: extractor/matcher model, descriptor paths, keypoint paths.
- `eval_results`: dataset split, model id, metrics, run date.

Suggested storage layout:

```text
backend/storage/google3d/
  permissions/
  aois/{aoi_id}/
    tiles/
    meshes/
    render_runs/{run_id}/
      rgb/
      depth/
      normal/
      poses/
      trajectory.json
      source_tiles.json
    features/{feature_run_id}/
    eval/{eval_run_id}/
```

## Coordinate Stack

Use explicit transforms at every stage.

- WGS84: lat/lon/height for global reference.
- ECEF: global metric math.
- ENU: local metric training/rendering frame per AOI.
- Scene-local: Gaussian splat / VPS scene coordinates.

Each AOI needs:

```json
{
  "aoi_id": "klcc_001",
  "origin_wgs84": {"lat": 3.1579, "lon": 101.7116, "h": 50.0},
  "origin_ecef": [0.0, 0.0, 0.0],
  "local_frame": "ENU",
  "vertical_datum": "documented_or_unknown"
}
```

Do not mix Google tile transforms, COLMAP coordinates, Unity coordinates, and VPS output without a transform registry.

## Synthetic Camera Generation

Generate views that approximate real VPS use, not flythrough marketing shots.

Camera policies:

- Pedestrian sidewalk: 1.4-1.8 m height, slow forward motion.
- Storefront sweep: 5-20 m from facade, lateral parallax.
- Vehicle path: road-aligned, 1.2-2.0 m height.
- Intersection turns: high yaw change, partial occlusions.
- Re-localization frames: sparse random frames around distinctive landmarks.
- Hard negatives: visually similar nearby facades and repeated urban patterns.

Each rendered frame should include:

- RGB image.
- Depth image where available.
- Normal image where available.
- Camera intrinsics.
- Camera extrinsics in ENU and ECEF.
- WGS84 camera position.
- Source tile ids.
- Render settings and augmentation flags.

Recommended render variants:

- FOV: 60, 70, 80 degrees.
- Resolution: 640x480, 1280x720, 1920x1080.
- Clean render plus augmented render.
- Augmentations: blur, compression, exposure shift, partial occlusion, crop, mild lens distortion.

## Training And Evaluation

Use the generated data in three layers:

1. Retrieval pretraining
   - Train place recognition and image retrieval.
   - Metrics: Recall@1, Recall@5, Recall@10.

2. Feature / matcher evaluation
   - Compare ORB, SIFT, SuperPoint, DISK, LoFTR, or other candidates.
   - Metrics: match count, inlier count, reprojection error, viewpoint robustness.

3. Pose localization benchmark
   - Use held-out camera trajectories.
   - Metrics: median translation error, p95 translation error, median rotation error, percentage localized under 0.5 m / 1 m / 3 m.

The important metric is synthetic-to-real transfer. Once one AOI has real phone capture, evaluate:

- Synthetic trained model on real frames.
- Real-only baseline.
- Synthetic pretrain + real fine-tune.

## Integration With Existing Project

Current pipeline:

```text
upload scan -> extract frames -> COLMAP -> splat -> feature DB -> /vps/localize
```

Google 3D pipeline should add a parallel synthetic dataset path:

```text
register AOI -> ingest tiles -> render synthetic frames -> build feature/eval dataset -> train/evaluate -> optionally seed VPS scene
```

Short-term integration points:

- Add `backend/services/google3d/` for AOI, tile, render, and dataset services.
- Add `backend/scripts/google3d_ingest_aoi.py`.
- Add `backend/scripts/google3d_render_dataset.py`.
- Add `backend/scripts/google3d_eval_features.py`.
- Reuse `backend/services/features/` for extractor comparison.
- Reuse `backend/storage/` provider abstraction for local/S3/Azure datasets.

Do not push Google 3D assets through the normal customer `Scene` model until the dataset pipeline is stable. Keep synthetic data separate from customer scenes.

## 30-Day Execution Plan

### Days 0-7: Access And AOI Setup

- Confirm permission document and create `data_permissions` record.
- Choose 3 AOIs:
  - dense urban,
  - storefront/retail street,
  - low-texture/open area.
- Implement WGS84/ECEF/ENU utilities.
- Render one AOI manually through a known-good viewer to validate access and visual quality.

Exit gate:

- One AOI can be loaded and viewed with correct geospatial origin.

### Days 8-15: Ingestion And Rendering

- Implement AOI tile traversal.
- Store tile metadata and source manifests.
- Build first deterministic camera policy.
- Render 10,000 clean RGB+pose frames for one AOI.
- Add depth/normal only after RGB+pose is reliable.

Exit gate:

- Dataset folder contains RGB images, pose JSON, trajectory manifest, and source tile manifest.

### Days 16-23: Baseline VPS Evaluation

- Run ORB/SIFT/SuperPoint or available feature extractors on synthetic frames.
- Build held-out query/reference splits.
- Produce first retrieval and pose benchmark report.
- Identify failure modes: repeated facades, weak ground-level detail, tile artifacts, scale/height issues.

Exit gate:

- One benchmark report compares at least two feature modes.

### Days 24-30: Synthetic-To-Real Check

- Capture a small real phone sample in or near one AOI if feasible.
- Compare real frames against synthetic-trained retrieval/features.
- Decide how Google 3D will be used:
  - pretraining only,
  - pretraining plus benchmark,
  - or production outdoor map initialization.

**Baseline results (unrelated scenes — KLCC synthetic vs indoor corridor real):**
| Metric | ORB | SIFT |
|--------|-----|------|
| Synth→Synth inlier ratio | 0.36 | 0.45 |
| Real→Real inlier ratio | 0.19 | 0.19 |
| Cross-domain inlier ratio | 0.11 | 0.15 |
| Transfer gap | 0.17 | 0.17 |

Script: `backend/scripts/synthetic_to_real_transfer.py` supports both DB and direct-path modes.
The transfer gap of ~0.17 is expected for unrelated scenes. A definitive result requires a phone capture at one of the 3 AOI locations (KLCC, Bukit Bintang, Merdeka Square). The gap may shrink significantly when comparing the same physical location across domains.

Exit gate:

- Go/no-go recommendation for scaling to 25 AOIs.

## Risks

- Rendered imagery may not match real phone imagery enough for direct localization.
- Google 3D may lack street-level details important for VPS.
- Tall buildings can cause coordinate/scale ambiguity if transforms are mishandled.
- Synthetic-only models may overfit to clean textures and perfect geometry.
- Outdoor success does not prove indoor pilot readiness.

## Decision

Proceed, but as a hybrid strategy:

- Google 3D for scale, synthetic pretraining, and benchmark generation.
- Real phone scans for production calibration and customer claims.
- Customer pilots remain measured against real captures, not synthetic-only benchmarks.
