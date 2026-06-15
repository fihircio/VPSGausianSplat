# Commercialization Weekly Execution Checklist

## Week 1

Focus: package the plan and start execution.

- Choose primary ICP for first outbound push.
- Select 50 target accounts.
- Draft pilot one-pager.
- Remove or qualify unsupported accuracy claims.
- Pick 3 Google 3D AOIs.
- Create permission metadata record format.
- Start WGS84/ECEF/ENU utility implementation plan.

Done when:

- Pilot offer can be sent to a buyer.
- AOI list and permission metadata are documented.

## Week 2

Focus: make the demo and data path real.

- Run 15-20 customer outreach attempts.
- Book first discovery calls.
- Make API/WebSocket base URLs environment-configurable.
- Start Google 3D AOI tile manifest proof of concept.
- Validate one AOI in a renderer.
- Draft benchmark JSON schema.

Done when:

- One AOI can be viewed or traversed.
- Demo no longer depends on editing hardcoded URLs.

## Week 3

Focus: produce first synthetic dataset.

- Continue outreach.
- Send first pilot proposal if a qualified lead exists.
- Generate deterministic camera path policy.
- Render first RGB+pose frame bundle.
- Add feature benchmark script plan.
- Create pilot success metric template.

Done when:

- First small synthetic dataset exists with images and pose JSON.
- Pilot metric template exists.

## Week 4

Focus: benchmark and sales proof.

- Render up to 10,000 RGB+pose frames for one AOI.
- Run baseline feature comparison.
- Produce first benchmark report.
- Record first demo video.
- Complete 10 discovery calls if possible.
- Send 3 proposals or identify why buyers are not ready.

Done when:

- Day-30 exit gates are reviewed.
- Go/no-go decision exists for scaling Google 3D ingestion.

## Week 5

Focus: pilot delivery shape.

- Start first paid pilot or internal pilot simulation.
- Add upload validation.
- Design API key auth model.
- Start Alembic migration setup.
- Add customer deployment checklist.
- Scale Google 3D to second AOI.

Done when:

- Pilot implementation scope is locked.
- Auth and migration approach are agreed.

## Week 6

Focus: make the platform safer.

- Implement API key auth for core APIs.
- Gate destructive/debug endpoints.
- Add basic tenant/project ownership model.
- Continue commercial outreach.
- Run Google 3D feature benchmark on second AOI.

Done when:

- Localization API has authenticated path.
- No unauthenticated destructive path remains for pilot use.

## Week 7

Focus: pilot experience.

- Package Unity SDK quickstart draft.
- Add SDK API key handling plan or implementation.
- Add scene readiness checklist in docs or UI.
- Create pilot result report template.
- Start synthetic-to-real check if field capture is available.

Done when:

- Developer can follow a written integration path.
- Pilot report format is ready.

## Week 8

Focus: repeatability.

- Add pytest coverage for core backend flows.
- Add frontend smoke test plan.
- Make storage path tenant/project scoped.
- Send second and third pilot proposals.
- Decide which commercial message is getting buyer response.

Done when:

- First pilot is delivered, scheduled, or blocked by a known external dependency.
- Repeatable deployment checklist exists.

## Week 9

Focus: conversion.

- Push first pilot toward expansion conversation.
- Add observability plan:
  - request ID,
  - localization latency,
  - confidence distribution,
  - worker phase timing.
- Harden WebSocket auth/rate-limit design.
- Scale Google 3D benchmark to third AOI.

Done when:

- Expansion path is defined for first pilot.
- Technical SLOs are drafted.

## Week 10

Focus: reliability.

- Add worker job table design.
- Add retry/cancellation/error category plan.
- Add seeded demo reset script plan.
- Create partner one-pager.
- Compare synthetic-only, real-only, and synthetic-pretrain approaches if data exists.

Done when:

- Demo reset and worker reliability tasks are ready for implementation.
- Partner message is clear.

## Week 11

Focus: packaging.

- Create 3-package pricing sheet:
  - Pilot,
  - Venue,
  - Network.
- Record updated demo video.
- Finalize SDK quickstart.
- Add CI gate plan for backend tests and frontend build.
- Draft case study if pilot customer permits.

Done when:

- Founder can pitch, demo, price, and propose without new materials.

## Week 12

Focus: decision and next quarter.

- Review signed pilots, proposals, and discovery call learnings.
- Choose winning ICP or pause weak segments.
- Decide Google 3D scale:
  - 25 AOIs,
  - research-only,
  - pretraining-only,
  - outdoor production initialization.
- Freeze next-quarter product roadmap.
- Prepare board/investor-style progress memo.

Done when:

- Day-90 exit gates are reviewed.
- Next 90-day plan is based on actual buyer and benchmark data.
