# Agent Task Board

## Active Workstreams

### Agent 1: Frontend Runtime Config

Scope:

- `frontend/lib/api.ts`
- `frontend/lib/TileManager.ts`
- `frontend/app/scenes/[id]/viewer/page.tsx`
- frontend env/docs if needed

Goal:

- Remove hardcoded localhost URL assumptions from the Next.js frontend.
- Add reusable API and WebSocket URL helpers.
- Keep storage URLs consistent through `toApiStorageUrl`.

Do not touch:

- Navigatus.
- Unity SDK.
- Backend.
- Google 3D scaffold.

### Agent 2: SDK And Navigatus Config

Scope:

- `navigatus/src/lib/vpsClient.ts`
- Navigatus env/readme files if needed
- `unity-sdk/com.vps.sdk/Runtime/Scripts/VPSClient.cs`
- Unity SDK docs/package metadata if needed

Goal:

- Make API base URL configurable.
- Prepare for API key support where simple.
- Improve timeout/error clarity if low-risk.

Do not touch:

- Next.js frontend.
- Backend.
- Google 3D scaffold.

### Agent 3: Google 3D Pipeline Scaffold

Scope:

- `backend/services/google3d/`
- `backend/scripts/google3d_*.py`
- optional Google 3D-specific docs/tests

Goal:

- Add offline-safe AOI registry utilities.
- Add WGS84/ECEF/ENU conversion utilities.
- Add deterministic camera path generation.
- Add a script that writes an AOI manifest skeleton from JSON.

Do not touch:

- Existing scene processing.
- Frontend.
- Navigatus.
- Unity SDK.

## Local Workstream

Scope:

- `docs/commercial/`
- commercialization coordination docs

Goal:

- Create Week 1 customer-facing assets:
  - pilot one-pager,
  - proposal template,
  - discovery call script,
  - target account research template.

## Integration Rules

- Preserve existing uncommitted work.
- Do not revert changes made by other agents or the user.
- Keep file ownership clean.
- Validate each workstream independently before merging next steps.
- Customer-facing claims must distinguish real validation from synthetic Google 3D benchmarks.
