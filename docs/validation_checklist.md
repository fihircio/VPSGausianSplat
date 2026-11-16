# VPS Validation Checklist (MVP)

## Goal
Verify whether VPS localization is viable on real scene data using the current backend pipeline.

## Prerequisites
- API server running
- Celery worker running
- PostgreSQL + Redis reachable
- COLMAP + ffmpeg installed in runtime environment

## Phase 1: Ingestion
1. Upload scene video:
   - `POST /scene/upload`
2. Save returned `scene_id`.

Pass condition:
- Scene exists in DB with status `UPLOADED`.

## Phase 2: Processing
1. Trigger processing:
   - `POST /scene/{scene_id}/process`
2. Poll scene status:
   - `GET /scene/{scene_id}`
3. Wait until status is `READY`.

Pass condition:
- `status == READY`
- `faiss_index_path` exists
- `feature_meta_path` exists
- `error_message` is null

## Phase 3: Mapping Sanity Check
Run:
```bash
python -m backend.scripts.validate_feature_mapping --scene-id <REAL_SCENE_ID> --frame-index 0
```

Inspect:
- Valid correspondences
- Unique 3D points

Pass guideline:
- Prefer `>= 50` valid correspondences for training frames.

## Phase 4: Existing Localization Diagnostic (Development Only)
Run batch evaluator:
```bash
python -m backend.scripts.test_localization --scene-id <REAL_SCENE_ID> --num-frames 20
```

This legacy evaluator samples reconstruction frames and sweeps ORB parameters. Use it to diagnose/tune a development scene only. Do not present its best configuration or scores as held-out customer validation: the sampled mapping frames are not an independent real-device query set.

Outputs:
- Console summary JSON
- Full report:
  - `backend/storage/debug/vps_evaluation_report.json`
- Debug images:
  - best/worst cases per configuration under `backend/storage/debug/`

## Phase 5: Held-Out Real-Device Benchmark (Pilot Evidence)

Use `backend.scripts.benchmark_localization` after a scene map is ready. It runs the existing localization service with its current configuration; it does not sweep or tune parameters. Queries must be real-device captures from a different capture session than the map build, and their independently measured poses must already use the map's `scene_local` coordinate frame.

Create a JSON manifest like this. Paths are absolute or relative to the manifest file. Keep synthetic Google 3D evaluations in their own reports; this runner rejects synthetic datasets.

```json
{
  "schema_version": "vps.real_benchmark.v1",
  "benchmark_id": "clinic-wing-device-check-01",
  "dataset_type": "real_device_capture",
  "split": "held_out",
  "scene_id": "<READY_SCENE_UUID>",
  "map_capture_session_id": "map-capture-2026-11-01",
  "coordinate_frame": "scene_local",
  "ground_truth_source": "independent surveyed control points and registered phone trajectory",
  "queries": [
    {
      "query_id": "query-0001",
      "capture_session_id": "heldout-capture-2026-11-03",
      "image_path": "queries/query-0001.jpg",
      "ground_truth": {
        "position_m": [1.2, 0.0, 3.4],
        "rotation_xyzw": [0.0, 0.0, 0.0, 1.0]
      },
      "metadata": {
        "site": "site-a",
        "device_model": "phone-model-and-build",
        "lens_mode": "main",
        "lighting": "indoor-evening",
        "location_tag": "corridor-east"
      }
    }
  ]
}
```

Run from the repository root with the same backend environment/database that contains the ready scene and feature index:

```bash
python -m backend.scripts.benchmark_localization --manifest path/to/benchmark_manifest.json
```

The script writes `<manifest>.report.json` by default, or accepts `--report <path>`. It reports localization success rate (pose returned and within all acceptance bounds), median/p95 translation and rotation error, median/p95 in-process localization latency, failure categories, and summaries by site, device, and lighting. Latency excludes HTTP, upload, and network time. It rejects map/query session reuse and exact query-image duplicates among locally accessible map frames; a report records any map frame images it could not inspect.

The output contract is versioned as `vps.real_benchmark.v1` and described by `backend/schemas/vps_real_benchmark_report.schema.json`. The runner intentionally does not store query images or raw estimated/ground-truth coordinates in its report.

Acceptance bounds are fixed in the runner to the existing MVP gates below: more than 30 inliers, confidence above 0.3, translation error below 0.5 m, and rotation error below 10 degrees. A minimum success rate of 0.6 is an initial pilot gate only; report sample count and conditions with every result. A pass on one site/device/lighting combination is not an SLA or a generalized accuracy claim. Do not tune on the held-out set. If the map and independently registered query poses cannot be expressed in the same scene coordinate frame, stop and collect/align the required ground truth instead of producing a score.

## Phase 6: Acceptance Criteria
VPS is considered working when majority results satisfy:
- `inliers > 30`
- `confidence > 0.3`
- `translation_error < 0.5`
- `rotation_error < 10`

Recommended project-level acceptance:
- `success_rate >= 0.6` on sampled frames

## Phase 7: Failure Diagnosis
For failed frames, inspect:
- `total_matches`
- `inliers`
- `failure_details.match_distance_stats`
- `failure_details.points3d_distribution`
- `diagnostic_flags`:
  - `LOW_MATCH_COUNT`
  - `POOR_3D_DISTRIBUTION`
  - `HIGH_REPROJECTION_ERROR`

## Phase 8: Tuning Sweep (Development Set Only)
Current script sweeps:
- ORB nfeatures: `500,1000,2000`
- pixel threshold: `3,5,8`
- ratio threshold: `0.7,0.8`

Use only a separate development/tuning set to pick:
- `best_config` from report
- Verify best config is stable across additional random frame samples

Never select a configuration from the held-out benchmark report. If parameters change after tuning, freeze the new configuration and score it on a fresh held-out capture batch.

## Runbook Notes
- Replace `<REAL_SCENE_ID>` with an actual UUID (no angle brackets in zsh command).
- Do not use mock data or reconstruction frames as final held-out viability evidence.
- Store each run report with timestamp if running multiple capture batches.
- Record the map capture session, query capture session, device/build, lens, lighting, site/area, ground-truth source, and sample count with every customer-facing result.
