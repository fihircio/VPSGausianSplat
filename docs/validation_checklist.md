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

## Phase 4: Localization Evaluation
Run batch evaluator:
```bash
python -m backend.scripts.test_localization --scene-id <REAL_SCENE_ID> --num-frames 20
```

Outputs:
- Console summary JSON
- Full report:
  - `backend/storage/debug/vps_evaluation_report.json`
- Debug images:
  - best/worst cases per configuration under `backend/storage/debug/`

## Phase 5: Acceptance Criteria
VPS is considered working when majority results satisfy:
- `inliers > 30`
- `confidence > 0.3`
- `translation_error < 0.5`
- `rotation_error < 10`

Recommended project-level acceptance:
- `success_rate >= 0.6` on sampled frames

## Phase 6: Failure Diagnosis
For failed frames, inspect:
- `total_matches`
- `inliers`
- `failure_details.match_distance_stats`
- `failure_details.points3d_distribution`
- `diagnostic_flags`:
  - `LOW_MATCH_COUNT`
  - `POOR_3D_DISTRIBUTION`
  - `HIGH_REPROJECTION_ERROR`

## Phase 7: Tuning Sweep
Current script sweeps:
- ORB nfeatures: `500,1000,2000`
- pixel threshold: `3,5,8`
- ratio threshold: `0.7,0.8`

Pick:
- `best_config` from report
- Verify best config is stable across additional random frame samples

## Runbook Notes
- Replace `<REAL_SCENE_ID>` with an actual UUID (no angle brackets in zsh command).
- Do not use mock data for final viability decisions.
- Store each run report with timestamp if running multiple capture batches.
