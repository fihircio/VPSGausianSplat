# VPSMAP — PC-side agent memory (OpenCode)

The Windows PC agent was the main workhorse for this project: **1,400 messages, 63 user turns,
1,005 shell commands, 201 file reads, 87 edits, 2.45 M input tokens**, spanning
**2026-06-16 → 2026-11-16** in a single OpenCode session (`ses_130944029ffehiGVN4yOpLVNZ1`,
agent `build`, model `opencode/glm-5.3-flash-free`).

This note is the distilled memory of that session. The source material and raw extraction live in
[opencode_sessions/pc-setup-vpsgausiansplat](opencode_sessions/pc-setup-vpsgausiansplat/):
`transcript_full.md` (chronological), `conversation_digest.md` (requests + commands + files),
`wrapups_only.md` (per-turn conclusions), `agent_messages.md`, `reasoning.md`.

Companion doc: [GEMINI_MEMORY.md](GEMINI_MEMORY.md) covers the Mac/Antigravity sessions
(2026‑04‑14 → 2026‑10‑18). This doc covers what happened **on the PC afterwards** — the part that
actually ran the pipeline on real GPU hardware.

> **Update 2026‑11‑16 — the working tree moved past this session.** The PC repo had a set of
> uncommitted changes dated **4–7 Nov 2026** that the exported session never mentions: upload
> validation hardening in `backend/api/routes_scene.py` (extension-driven media kind, generic MIME
> tolerance, size measurement for non-seekable uploads), a frontend refresh (home/scenes/upload/
> Navbar/layout), rewritten commercial docs, a **30-day discovery outreach plan**, a **real-benchmark
> report schema** (`backend/schemas/vps_real_benchmark_report.schema.json`) and
> `backend/scripts/benchmark_localization.py`. These were committed as **`1a16711`** ("capture Nov
> baseline…") and pushed to `origin/main`, together with `.gitignore` entries for the local SQLite DB,
> CORS runtime file, logs and scratch scripts.
>
> **The database changed too:** `backend/.env` now reads
> `DATABASE_URL=sqlite:///./backend/storage/vps.db` (SQLite, last written 7 Nov 2026), not Postgres.
> `psycopg` is still in `requirements.txt`, so switching back is one env var away. `db.py` now sets
> `journal_mode=WAL`, `synchronous=NORMAL`, `busy_timeout=15000` and `foreign_keys=ON` on every SQLite
> connection (`e7ddab7`) — verified on the PC: pragmas take effect and a second writer waits (~2.6 s)
> instead of failing. See [docs/database.md](docs/database.md).
>
> **Corrections to the notes below, verified on the machine (2026‑11‑16):**
> - `win_exec` runs **elevated** (`user` is a member of Administrators) — the "no admin rights"
>   limitation no longer applies; firewall rules, services and the page file are all changeable.
> - **Tailscale was reinstalled on 2026‑11‑16 04:42** and is now logged out (`NoState`, "No serve
>   config"). It needs an interactive `tailscale up`. The Mac and PC are currently on the **same LAN**,
>   so `http://192.168.50.62:3000` works without Tailscale.
> - Servers must be spawned **detached from the SSH session** (`Win32_Process.Create` via CIM);
>   `Start-Process` children die when the SSH command returns.
> - Postgres is **not** needed any more; Redis 3.0.504 runs as a service and answers `PONG`.

## The machine (PC-side facts, not in git)

| Item | Value |
|---|---|
| Host | Windows PC `desktop-578pjun`, Ryzen + **RTX 5060 (Blackwell, sm_120)**, **no admin rights** |
| Project path | `D:\WORKS\2026\20260308_VPSMAP\WIP\VPSGausianSplat` (later a `VPSGausianSplat2` clone) |
| Ports | backend **8002** (8000 is system-reserved), frontend **3000**, navigatus **3001** |
| PostgreSQL | **17.5 portable** at `C:\pgsql17\pgsql`, data `C:\pgsql_data`, `:5432`, user/db `vps`/`vps`. Runs as a process, *not a service* — dies on reboot |
| Redis | 3.0.504, `:6379` |
| Tailscale | PC `100.118.54.14`, Mac `100.120.137.118`; **Tailscale Serve** publishes `http://desktop-578pjun.tail9e0bfc.ts.net:3000` → `127.0.0.1:3000` |
| ngrok | used only in the first day; replaced by Tailscale |
| COLMAP | `C:\colmap\bin\colmap.exe` — CUDA build; its DLLs must sit next to the exe (`cudart64_12.dll`), and every call needs `QT_QPA_PLATFORM=offscreen` |
| Blender | 5.0.1 at `C:\Program Files\Blender Foundation\Blender 5.0\blender.exe`, wired as `BLENDER_BIN` |
| Python | backend runs from `backend/.venv` (the hermes venv had torch DLL failures); `FEATURE_MODE=ORB` to avoid loading torch |
| Secrets | `backend/.env` and `frontend/.env.local` are **gitignored** on the PC: `COLMAP_BIN`, `DEFAULT_VIDEO_FPS=4`, `GOOGLE_API_KEY`, `NEXT_PUBLIC_API_BASE_URL=http://100.118.54.14:8002`, `NEXT_PUBLIC_WS_BASE_URL=ws://100.118.54.14:8002` |

## Start / stop recipe (as the last session left it)

```powershell
# 1. Datastores (Postgres is a process, not a service)
C:\pgsql17\pgsql\bin\pg_ctl.exe -D C:\pgsql_data -l C:\pgsql_data\pg.log start
# Redis already auto-starts (winget install)

# 2. Backend — from the project ROOT, with the project venv
backend\.venv\Scripts\python.exe -m uvicorn backend.api.main:app --host 0.0.0.0 --port 8002

# 3. Frontend — must bind 127.0.0.1 so Tailscale Serve can proxy it
$env:HOSTNAME="localhost"; npm run dev        # in frontend/, port 3000

# 4. Check
curl.exe http://127.0.0.1:8002/               # -> {"status":"ok"}
tailscale serve status
```

Next.js **must** listen on `127.0.0.1:3000`; if it binds only to the Tailscale IP, Serve returns
**502** (that was the last bug fixed on 2026‑10‑21).

## Pipeline fixes that made it work on this hardware

1. **COLMAP for video, not panoramic**: `sequential_matcher` with overlap 10 (was
   `exhaustive_matcher`, which failed every multi-frame video). Registration gate lowered to 20%;
   `init_min_inliers` 30→15, `abs_pose_min_num_inliers` 8→6. Frame extraction default **4 fps**.
2. **Camera model**: `SIMPLE_RADIAL` → `SIMPLE_PINHOLE` in `reconstruction.py`, plus
   `SIMPLE_RADIAL` support added in `gaussian-splatting/scene/dataset_readers.py` so older scenes still train.
3. **Best model promotion**: after `model_converter`, the best sparse model is copied to `sparse/0/`
   so downstream stages always find all images.
4. **Splatting**: `sys.executable` (was hardcoded `"python"` → wrong interpreter), output to a log
   file, final PLY copied to `point_cloud.ply`. With `GAUSSIAN_SPLATTING_REPO` set, 30 k iterations
   gave **PSNR 33.6 and a 180 MB PLY (~25 min)**; without it the service writes a *sparse fallback PLY*.
5. **CUDA on sm_120**: PyTorch CUDA works for basic ops; `diff-gaussian-rasterization` was compiled
   for **sm_120** and trains; `gsplat` 1.5.3 is a pure-Python wheel with no usable kernel, so it was rejected.
6. **Celery removed from the hot path**: torch DLL/page-file crashes on `C:` → the scene pipeline now
   runs in a daemon thread inside the API (`routes_scene.py:181`). Verified in the repo.
7. **Storage**: `STORAGE_ROOT` absolute; `C:` freed 0 → 20 GB (temp cleanup).
8. **Feature loading**: lazy `torch`/`kornia` import in `backend/services/features/feature_factory.py`
   so ORB mode never loads them — commit `3d8bc18`, the last commit on `main`.
9. **Google 3D**: all modules (`tile_downloader`, `scene_builder`, `mesh_renderer`,
   `dataset_generator`, `rendering`, `aoi`, `camera_paths`, `transforms`, `manifest`) were written
   and import cleanly; Blender headless verified. **Tile ingestion never ran** — AOI manifests still say
   `not_ingested`, so the render dataset is empty.

## Web/portal fixes (Windows + Tailscale specific)

- Initial ngrok tunnel, then **Tailscale** peer-to-peer (both machines on the same tailnet).
- Windows Firewall has inbound **Block** rules for `node.exe` / `python.exe` on the Private profile;
  the AI had no admin rights to delete them. Workaround: **Tailscale Serve** (proxies from its own process).
- A backend reverse proxy was added to dodge the firewall, then **removed** — it broke binary
  responses with `ERR_CONTENT_DECODING_FAILED` (httpx decompressed the body but kept `Content-Encoding: gzip`).
- Final architecture: frontend on `:3000` with Next.js **rewrites** to `localhost:8002`, relative API
  calls (single origin, no CORS). Later, binary PLY fetches were moved to go **directly** to
  `http://100.118.54.14:8002` because the Next.js dev proxy hung on large binary files over Tailscale.
- Next.js 16 blocked the Tailscale hostname (`Blocked cross-origin request to /_next/webpack-hmr`);
  fixed by adding `allowedDevOrigins` for `desktop-578pjun.tail9e0bfc.ts.net` and `100.118.54.14` — commit `c358b3b`.

## Scenes as the PC session left them

| Scene | What | State |
|---|---|---|
| `57528008-4a09-4da7-9a96-c5b292213645` | PSIKIATRIK_1 (25 s, 848×478): 51 frames, **51/51 registered**, 959 points, 3DGS 30k PSNR 33.6 (180 MB), FAISS **2,775** descriptors | READY — first full E2E pass; `/vps/localize` on frame 11 gave **20 inliers**, pos `[0.82, 0.92, -4.30]`, confidence 6.4% |
| `299a4c07-c927-431c-b397-123d959f4e7b` | Psychiatry Wing, first attempt (long raw video) | FAILED — 0% frames registered (too sparse motion/texture) |
| `8528a856-1b83-4ba3-aab0-4ede76aefb77` | Psychiatry Wing, reprocessed with `sequential_matcher` at 4 fps | READY — **496 frames**, sparse fallback PLY (66 KB) + FAISS; viewer at `.../scenes/8528a856.../viewer` |

The Psychiatry Wing viewer shows the **sparse fallback PLY, not a trained 3DGS** — `GAUSSIAN_SPLATTING_REPO`
was not set when it was processed.

## Execution-plan work delivered from the PC (`docs/execution_prompts.md`)

| Prompt | Delivered | Commit |
|---|---|---|
| 1 Spatial hints | `hint_position`/`hint_radius`/`hint_floor_height`/`geo_hint`, `hint_used`; 61 vs 20 inliers on test scene | `184f608` |
| 2 Multi-frame VPS | `POST /vps/localize/multi` (4–6 images, merged correspondences, single PnP) + frontend/navigatus UI | `c664876` |
| 3 JWT auth + resize | `/auth/token`, `/auth/register`, `require_scope()`, 1280 px resize; legacy `X-API-Key` kept | `184f608` |
| 4 Part A | navigatus 1280 px capture + race fix | `184f608`, `978b624` |
| 7 CORS UI + analytics | settings page, analytics dashboard, Redis metrics | `4b76585` |
| 8 `@vps/web-client` | `packages/vps-webxr/` — `VpsClient`, types, `connectVpsWebSocket`, built `dist/` | `5372ee8` |
| 9 Unity SDK expansion | multi-frame + hints + sample scenes | `813897d` |
| Blender wiring | `blender_bin` setting, headless verified | `7d24990` |

Still open per the plan: Prompt 4 Part B / 8-equivalent WebXR package (delivered in code but the local doc
still lists it OPEN), Prompt 10 E2E validation, Prompt 11 field capture at a synthetic AOI, and the Google 3D
tile ingestion.

## Git: what is actually on `main`

Verified `git ls-remote` on 2026‑11‑16: remote `main` tip is **`3d8bc18`**
(`backend/services/features/feature_factory.py` lazy torch/kornia import), on top of
`c358b3b` (Tailscale `allowedDevOrigins`), `58c9d36` (sequential_matcher + COLMAP thresholds),
`b2a8b12`, `813897d`, `5372ee8`, `c664876`, `7d24990`, `4b76585`, `184f608`, `093461b`.

The Mac checkout in `WIP/` sits at `813897d` — **behind** the PC's pushes by 2+ commits, so
`git pull` before comparing local code with anything described here.

### One incident worth remembering

The PC agent tried to purge a **788 MB `torch_cu130.whl`** from git history with `filter-branch`, killed
pack files mid-operation and **corrupted the repo**. It recovered by cloning fresh (`VPSGausianSplat2`,
`origin/main` @ `184f608`) and re-applying Prompt 2 changes, then the human rebuilt `.git`. Lesson:
never filter history with uncommitted work in the tree; large binaries belong in `.gitignore` or LFS.
Untracked artefacts from that episode (`geminiconvo.md`, `run_worker.ps1`, `torch_cu130.whl`,
`test_query.jpg`, `validation_report_agent_mac.md`) must not be committed.

## Open threads / where it stopped

- **Servers were shut down on 2026‑10‑21**; the last request of the session (2026‑10‑28) got no reply.
  **Restarted on 2026‑11‑16** and verified: backend `:8002` (`/health` 200), frontend `:3000`
  (`/scenes` and the Psychiatry Wing viewer 200, PLY 200), Redis `:6379` PONG. Access from the Mac over
  LAN at `http://192.168.50.62:3000`; Tailscale needs a re-login.
- **Measured localization accuracy** ([docs/validation_self_eval_psikiatrik.md](docs/validation_self_eval_psikiatrik.md)):
  on scene `8528a856`, success under inliers ≥ 30 / ≤ 0.5 units / ≤ 10° was **8.3 % (1/12)** and
  **2.5 % (1/40)**. Solved frames sit at 2–5 cm translation error (consistent with the published
  0.036 m), but rotation error reaches 94–107° on some of them, and rejected frames had 400–536 matches
  with only 6–13 inliers. The README's **95 % success rate is not supported** by this scene.
- Google 3D pipeline is one step from useful: needs the Maps Tiles ingestion run for a KL AOI before
  Blender can render a dataset.
- `navigatus` never compiled after the repo re-clone.
- 3DGS for Psychiatry Wing was never trained (fallback PLY only) — and only 333 of 496 frames registered
  in COLMAP, so a third of that capture has no ground truth.
- `backend/scripts/test_localization.py` is stale (calls `FeatureMapper.extract_orb_features`, which no
  longer exists); use `backend/scripts/evaluate_localization.py` instead, or delete it.
- Security hygiene: the ngrok auth token and the Google Maps API key were pasted into this chat log. If
  those values are still live, rotate them; keep keys in `backend/.env` only.

## Provenance

Source export: `/Users/fihiromar/Desktop/pc-setup-for-vpsgausiansplat-project.json` (8.4 MB).
Extraction: `opencode_sessions/pc-setup-vpsgausiansplat/` — see its `README.md` for the field table and
`wrapups_only.md` for the 63 turn conclusions quoted above. Repo facts (threading, health route,
package contents, git tip) were re-verified against this checkout rather than taken from the session
transcript.
