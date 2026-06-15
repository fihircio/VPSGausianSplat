# Google 3D Agent Handoff

## Objective

Build a Google 3D synthetic data pipeline that supports VPS model pretraining, feature/matcher evaluation, and outdoor geospatial demo generation.

Assumption: permission exists to use Google Maps / Google Photorealistic 3D data for training and commercial model development. Agents must still record permission scope in metadata before dataset jobs run.

## Workstream A: Data Access And AOI Registry

Owner: data ingestion agent.

Deliverables:

- AOI registry format with WGS84 polygon, origin WGS84, origin ECEF, and local ENU frame.
- Permission metadata format.
- Google 3D tile traversal proof of concept for one AOI.
- Source tile manifest JSON.

Suggested files:

- `backend/services/google3d/aoi.py`
- `backend/services/google3d/tiles.py`
- `backend/scripts/google3d_ingest_aoi.py`
- `docs/google_3d_training_pipeline.md`

Acceptance:

- Given an AOI polygon, the script writes a tile manifest with tile ids, transforms, bounding volumes, and source URIs.
- No customer `Scene` records are created yet.

## Workstream B: Coordinate And Transform Registry

Owner: spatial engine agent.

Deliverables:

- WGS84/ECEF/ENU conversion utilities.
- Transform registry for provider coordinates, render coordinates, VPS scene coordinates, and Unity coordinates.
- Tests for round-trip conversion.

Suggested files:

- `backend/utils/geo.py`
- `backend/services/google3d/transforms.py`
- `backend/scripts/validate_google3d_transforms.py`

Acceptance:

- AOI origin can convert WGS84 -> ECEF -> ENU -> ECEF -> WGS84 with acceptable numerical error.
- Frame poses include both ENU and ECEF extrinsics.

## Workstream C: Synthetic Camera And Renderer

Owner: rendering/dataset agent.

Deliverables:

- Deterministic camera path generator.
- Headless rendering path that outputs RGB images and pose JSON.
- Dataset manifest format.
- Optional augmentation pass.

Suggested files:

- `backend/services/google3d/camera_paths.py`
- `backend/services/google3d/rendering.py`
- `backend/scripts/google3d_render_dataset.py`

Acceptance:

- One AOI produces at least 10,000 RGB+pose frames.
- Every frame has intrinsics, ENU extrinsics, ECEF extrinsics, WGS84 camera position, and source tile ids.

## Workstream D: Feature Benchmark And Model Evaluation

Owner: VPS evaluation agent.

Deliverables:

- Synthetic reference/query split generator.
- Feature extraction benchmark over existing extractors.
- Retrieval and localization metrics report.
- Comparison against current ORB/SIFT baseline.

Suggested files:

- `backend/services/google3d/dataset.py`
- `backend/scripts/google3d_eval_features.py`
- `backend/scripts/google3d_build_feature_index.py`

Acceptance:

- Report includes Recall@1, Recall@5, match counts, inliers, median translation error, and median rotation error.
- Benchmark can run repeatedly on a fixed dataset and produce comparable JSON output.

## Workstream E: Product And Commercial Pilot Alignment

Owner: commercialization/product agent.

Deliverables:

- Clear positioning for Google 3D:
  - synthetic pretraining,
  - outdoor demo acceleration,
  - benchmark generation,
  - not a replacement for production customer scans.
- Pilot plan updated to explain where Google 3D helps and where real capture remains required.
- Customer-safe accuracy language.

Suggested files:

- `docs/demo_walkthrough.md`
- `docs/validation_checklist.md`
- pitch deck / sales one-pager if requested.

Acceptance:

- No customer-facing claim says synthetic Google 3D alone proves production VPS accuracy.
- Pilot success metrics remain based on real device validation.

## 30-Day Milestone

By day 30, the team should demonstrate:

1. One Google 3D AOI ingested into a source manifest.
2. One local ENU coordinate frame validated.
3. 10,000 rendered RGB+pose frames.
4. One feature benchmark report comparing at least two feature modes.
5. One small real-device sample evaluated against the synthetic pipeline, if field access is feasible.
6. Decision memo: scale to 25 AOIs, keep as research-only, or use only for pretraining.

## Non-Goals For First 30 Days

- Do not build a full self-serve Google 3D importer.
- Do not mix Google 3D synthetic datasets with customer scenes in the same model tables.
- Do not promise indoor VPS benefits from outdoor synthetic data until measured.
- Do not spend time on billing, marketplace packaging, or broad SDK work inside this workstream.
