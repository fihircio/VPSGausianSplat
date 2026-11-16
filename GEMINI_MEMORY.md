# VPSMAP — recovered Gemini / Antigravity memory

Everything recoverable from Antigravity for the **VPSGausianSplat / VPSMAP** project (workspace
`20260308_VPSMAP/WIP`, now on `/Volumes/macos11`). 11 conversations, 4,735 steps, spanning
**2026-04-14 → 2026-10-18**. Each folder has `conversation_full.md`, `conversation_condensed.md`,
`DIGEST.md`, `steps.json`, `build.py`.

## The 11 conversations

| Date range | Steps | Theme | Folder |
|---|---|---|---|
| 04-14 → 04-23 | **1692** | **Main thread**: COLMAP setup, first real-video E2E, 4.1 cm success, 3D viewer, agent handoff protocol, colmap_image bug, 1241-frame run, binary-PLY perf | [3ca28de7](antigravity_conversation_3ca28de7/DIGEST.md) |
| 04-14 → 04-20 | 660 | Subagent: Phase 1 feature extraction → Phase 4.3 presence viz → 4.2 sync | [ae185df7](antigravity_conversation_ae185df7/DIGEST.md) |
| 04-14 → 04-20 | 242 | Subagent: Unity SDK lead → Phase 4.1.3 hybrid SIFT + calibration | [9a336750](antigravity_conversation_9a336750/DIGEST.md) |
| 04-14 → 04-20 | 301 | Subagent: cloud-ready storage (S3/Azure) → Phase 4.2 tracking | [73d52093](antigravity_conversation_73d52093/DIGEST.md) |
| 04-15 → 04-21 | 381 | Subagent: visualization track — anchors, tiling, splat viewer | [b565db69](antigravity_conversation_b565db69/DIGEST.md) |
| 04-15 → 04-22 | 848 | Controller/terminal agent: env fixes, progress bar, Phase 4 verification + commits | [4c388c4e](antigravity_conversation_4c388c4e/README.md) |
| 06-15 | 567 | Codex continuation: API-key auth, upload gating, Google‑3D AOIs, synthetic renderer, commercial docs, tests | [75d668b7](antigravity_conversation_75d668b7/README.md) |
| 06-15 | 4 | Spawn prompt: Unity SDK QUICKSTART.md (never executed — quota) | [420a9353](antigravity_conversation_420a9353/DIGEST.md) |
| 06-15 | 4 | Spawn prompt: 3 commercial docs (never executed — quota) | [f3a5b9ee](antigravity_conversation_f3a5b9ee/DIGEST.md) |
| 06-15 | 4 | Spawn prompt: backend pytest gating tests (never executed — quota) | [7e88acc1](antigravity_conversation_7e88acc1/DIGEST.md) |
| 10-15 → 10-18 | 32 | WBS breakdown + quotation revision (single floor vs multi-level Option B) | [30376c7a](antigravity_conversation_30376c7a/DIGEST.md) |

## Narrative — how the project actually got built

**Phase 0 — prove the pipeline (Apr 14).** The main thread starts with
`python -m backend.scripts.test_localization --scene-id 123e... --num-frames 20`. Docker/Postgres had to
move to **5433**, COLMAP was installed via `brew install colmap`, and the first videos were AI-generated
(Google Flow) before switching to a real hospital walkthrough. The breakthrough moment the user pasted:
*"4.1 cm Euclidean Distance, 0.18 deg Rotation Offset"* — the first successful 6DoF localization. Then a
CMO/investor demo portal was built, the 3D viewer added (`GridHelper`/`AxesHelper`, frame thumbnails, blue
camera markers), and `npm run build` fought Node 18.17 vs Next.js 16.

**Phase 0.5 — governance.** The user asked for a checklist + handoff flow so *"other agents execute all the
phases"*, and the Controller validates each agent's work before the next one proceeds. That produced
`docs/roadmap_checklist.md` + `docs/agent_handoff_protocol.md`, and four parallel agent conversations
were kicked off on 04-14/04-15 with rigid prompts (allowed files, forbidden files, plan-first).

**Phase 1–4 — parallel agent rollout.** Feature extraction upgrade (Kornia, SuperPoint → DISK, feature
modes, FAISS); cloud storage abstraction (`get_storage()`, local/remote sync); Unity SDK (`com.vps.sdk`,
`VPSClient.cs`); visualization (anchors, octree tiling, `TileManager`, glassmorphism viewer). The
Controller (4c388c4e) then verified and committed: anchors CRUD, `AgentSession`, WebSocket sync
(`/ws/vps/agents/{scene_id}`), heartbeat pruning, background pose persistence to Postgres.
Hybrid localization was added later: SIFT fallback when primary inliers < 30 or confidence < 0.25, plus
`calibrate_scene.py` (Kabsch 7-DOF similarity transform, `calibration.json` auto-applied).

**Phase 5 — real-scene reality check (Apr 22–23).** Back on the main thread: the `colmap_image` NameError
kept recurring, a 1241-frame video took hours in COLMAP, the 3D render wasn't centered on the COLMAP
frame, and scene loading hung at *"Decoding Spatial Layers: 0%"*. Fixed by writing **binary PLY**
(5.7 MB → 1.2 MB, ~10–30 s → 1–2 s). Scene `PSIKIATRIK_FULL` is the reference large scene.

**Phase 6 — commercialisation (Jun 15).** Codex hit its token limit mid-90-day-plan; Gemini picked it up:
API-key auth (`backend/api/auth.py`, `x-api-key` on `/localize`, upload, `/process`, `/cleanup`,
`DELETE /anchors/{id}`), debug endpoint gating, upload type/size validation, Google‑3D synthetic data engine
with three real KL AOIs (`klcc_001`, `bukit_bintang_001`, `merdeka_square_001`), procedural renderer +
ORB/SIFT benchmark, `docs/schemas/evaluation_schema.json`, commercial templates, and a pytest gating suite.

**Phase 7 — pricing (Oct 15–18).** WBS breakdown then quotation revision: the draft had VPS bullets pasted
onto an old KPI/HR template (wrong header, Flutter/.exe/.dmg claims) — corrected to FastAPI/VPS wording,
with Option A (single floor) and Option B (multi-level ~4,000–6,000 m², 3–4 floors) costing.

## Architecture snapshot (as of the last sessions)

- **Backend** `backend/`: FastAPI (`api/main.py`, `routes_scene.py`, `routes_vps.py`), Celery worker
  (`workers/tasks.py`), SQLAlchemy + Postgres **5433** (Docker), Redis. Pipeline:
  extract_frames → COLMAP (`sequential_matcher`) → Gaussian splatting → feature index (FAISS, feature_mode
  ORB/DISK/SIFT) → localization via `cv2.solvePnPRansac` → evaluation report JSON.
  Storage abstracted behind `get_storage()` (local disk ⇄ S3/Azure), `.venv` Python **3.12**.
- **Spatial layer**: `Anchor` model + CRUD, `AgentSession`, `sync_service.py` WebSocket broadcaster,
  `scripts/tile_splat.py` octree tiling + manifests, `calibrate_scene.py`.
- **Frontend** `frontend/`: Next.js app router — `/scenes/[id]`, `/scenes/[id]/viewer`, `/localize`;
  three.js + `@mkkellogg/gaussian-splats-3d`, `TileManager` (frustum culled streaming),
  `AnchorManager` (GLB placement), progress bar (`progress_percent` / `current_task_label`).
- **Clients**: `unity-sdk/com.vps.sdk` (`VPSClient.cs`), `navigatus` (web client), `packages/` incl.
  later `@vps/web-client`. Multi-frame localization + spatial hints (`hintPosition`, `hintFloorHeight`,
  `geoHint`) came in the later git history (Prompt 6–9).
- **Google‑3D synthetic engine**: `backend/services/google3d/` (`aoi.py`, `manifest.py`, `transforms.py`,
  `camera_paths.py`, `rendering.py`, `aoi_registry.json`) + `scripts/google3d_ingest_aoi.py`,
  `google3d_render_dataset.py`, `google3d_eval_features.py`, `google3d_validate_transforms.py`.
- **Security**: API key validation HTTP + WebSocket, `allow_debug_endpoints` gate, upload
  extension/size caps, `.env.example` security block.

## Bug → fix ledger

| Symptom | Real cause | Fix |
|---|---|---|
| `ModuleNotFoundError: boto3` (then `kornia`, `lightglue`) | installed into Anaconda while the app ran `.venv` (which had both py3.12 and py3.14 lib dirs) | install with `.venv/bin/python3.12 -m pip` |
| `Pipeline Error: name 'get_storage' is not defined` | missing import in `splatting.py` + `feature_mapper.py` | add `from backend.utils.storage import get_storage` |
| `name 'FeatureService' is not defined` | module shadowing — `services/features.py` **and** `services/features/` | renamed file to `feature_service.py`, updated `vps.py`, `test_localization.py` |
| `name 'colmap_image' is not defined` (recurring) | loop-local variable + collision with `ColmapImage` class | rename to `registered_image`, initialise before loop *(status unverified)* |
| backends working on wrong DB | two Postgres instances 5432 & 5433; migration applied to 5433 | unify `.env`/compose to 5433, restart both |
| progress bar never appears | stale backend + old Celery worker on stale code | kill/restart worker `--concurrency=1`, re-queue scene |
| `npm run build` fails | Node 18.17 vs Next 16 (≥20.9); duplicate ternary in viewer page; multiple lockfiles | Node 20, remove duplicate block, set turbopack root |
| 3D viewer blank / PLY 404 | static mount path vs `to_web_path` mismatch | fix storage mount + fallback path handling |
| splat not centered | alignment against COLMAP frame | viewer fit-scene / re-align step |
| *"Decoding Spatial Layers: 0%"* hang | ASCII PLY 5.7 MB parsed line-by-line | write **binary** PLY: 1.2 MB, ~1–2 s |
| `ForeignKeyViolation` in pose persistence | `test-scene` mock id persisted to `agent_sessions` | validate `scene_id` exists before persist |
| pytest needs live Postgres | `engine = create_engine(...)` at import time in `db.py` | lazy `_get_engine()` |
| dependency overrides ignored in tests | `validate_api_key` called `get_settings()` directly | `Depends(get_settings)` |

**Not a bug, but the reason sessions kept "stopping strangely":** repeated
`UNAVAILABLE (503) No capacity for claude-sonnet-4-6 / gemini-3-flash-agent` and
`RESOURCE_EXHAUSTED (429) Individual quota reached, resets in ~167h`. Almost every "can u continue?" turn in
these transcripts is a quota retry, not a logic failure.

## Standing rules the user imposed (carry these forward)

1. **Plan-first protocol** — every agent prompt must say: read `docs/roadmap_checklist.md` +
   `docs/agent_handoff_protocol.md` → present an `implementation_plan.md` → **wait for USER approval** →
   execute → finish with `validation_report_<role>.md`.
2. **Explicit file allow/deny lists** per agent (e.g. "do NOT touch `backend/utils/storage.py` or
   `backend/services/`", "do NOT touch `backend/workers/tasks.py`").
3. **Controller validates before commit** — the user repeatedly pasted a finished agent's report and asked
   *"check whether it's finished, if it is, push to commit the files that have passed checking"*.
4. **Scope decisions**: no surgical overlay — this is **indoor mapping for public hospital users**
   only; don't wait for real medical GLBs (use Khronos sample models); KL AOIs for synthetic data.
5. **Accuracy claims must be qualified** — the 4.1 cm result is a test outcome, not a product guarantee.
6. **Run from the WIP root**: `source .venv/bin/activate` + `uvicorn backend.api.main:app` (or
   `PYTHONPATH=. python -m backend.api.main`) — running from `backend/` breaks `backend.*` imports.
7. **Git hygiene**: exclude `*.mp4`, `*.MOV`, `*.txt`, `backend/storage/debug/`, `backend/scratch/`.

## Open threads at the end of the recorded memory

- **8 failing pytest tests** in `backend/tests/test_api_gating.py`: 413 never triggers because
  `UploadFile.size` is `None` under `TestClient`; `cleanup`/`delete_anchor` 403 checks run after a
  mocked `db.get()` returns `None` (404 wins) — flag check must precede the DB lookup; `debug_path` still
  reads real settings. The two structural fixes (lazy engine, `Depends(get_settings)`) *are* in the repo.
- `colmap_image` / `registered_image` rename and the 3D-centering fix were proposed but never confirmed.
- Phase 5 (SDK & mobile AR, predictive analytics / collision avoidance) was announced as "next" but the
  git history jumps to Prompt 6–9 (multi-frame, spatial hints, CORS UI, analytics, `@vps/web-client`).
- Quotation: Option B (multi-level) breakdown written; client-facing final quote not confirmed.

## Recovering more / re-running

Antigravity's `conversations/<id>.pb` are encrypted (entropy 8.0, no gzip/zstd/lzma magic). The running
language server decrypts them over connectrpc — port + token from
`~/.gemini/antigravity/daemon/hub_*.json`:

```bash
HUB=~/.gemini/antigravity/daemon/hub_60937.json
PORT=$(python3 -c "import json;print(json.load(open('$HUB'))['httpPort'])")
TOKEN=$(python3 -c "import json;print(json.load(open('$HUB'))['csrfToken'])")
curl -s -X POST "http://127.0.0.1:$PORT/exa.language_server_pb.LanguageServerService/GetCascadeTrajectorySteps" \
  -H "Content-Type: application/json" -H "x-codeium-csrf-token: $TOKEN" \
  -d '{"cascadeId":"<conversation-id>"}' -o steps.json
python3 build.py    # regenerate conversation_full.md / conversation_condensed.md
```

`GetAllCascadeTrajectories` (POST `{}`) lists every conversation with workspace + step count. Other
Antigravity conversations on this machine (other projects: EVENTPORTAL, RAIKANBERSAMA, STAGECANVAS,
VETERINARVR, LUNICOTIRAMISU, AIMSVET, ENDOSKELETON) are listed in
`antigravity_conversation_4c388c4e/conversation_summaries.db` if you ever need those too.
