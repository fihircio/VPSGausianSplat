# Roadmap Checklist: Phase 5 (Commercialization And Google 3D Data)

Status reviewed 2026-11-04 against the current checkout. `[x]` means the artifact or code exists, not that it is production-ready or independently validated. `[~]` means partially implemented. This is not a record of customer outreach or pilot results.

## Module 1: Commercial Pilot Package
- `[x]` Create customer-facing one-page pilot offer.
- `[x]` Create pilot proposal template.
- `[x]` Create pilot success metric template.
- `[~]` Create internal security/privacy response guide; it is not an approved customer FAQ or security assurance.
- `[ ]` Record 2-minute demo video.
- `[x]` Draft internal pricing hypotheses for a bounded pilot; no validated Venue/Network packages or willingness-to-pay evidence.

## Module 2: Google 3D Synthetic Data Engine
- `[x]` Document permission metadata record.
- `[x]` Select 3 AOIs: dense urban, storefront, low-texture/open.
- `[x]` Implement AOI/source manifest scaffolding; actual Google tile ingestion is not complete (`source_tiles.json` entries are empty/not ingested).
- `[x]` Implement WGS84/ECEF/ENU coordinate utilities.
- `[x]` Generate deterministic synthetic camera paths.
- `[ ]` Render 10,000 RGB+pose frames for first AOI. KLCC currently has 10,000 pose-metadata rows, but no rendered RGB/depth files or ingested source tiles in this checkout.
- `[x]` Save an exploratory ORB/SIFT feature benchmark artifact (500 sampled frames); this is not a held-out end-to-end localization benchmark.
- `[ ]` Complete a matched-location synthetic-to-real validation. The saved cross-domain diagnostic compares KLCC synthetic data with an unrelated indoor corridor and is not transfer evidence for the same site.

## Module 3: Pilot-Ready Engineering
- `[~]` Make API URLs configurable in frontend, Navigatus, and Unity REST client; viewer WebSocket proxy/config and Unity WebSocket endpoint still need work.
- `[x]` Add upload size/type validation.
- `[x]` Gate destructive and debug endpoints.
- `[~]` Add basic API-key/JWT components. Consistent authorization across routes is incomplete, and `NEXT_PUBLIC_API_KEY` is exposed in the browser bundle.
- `[~]` Add tenant/project model scaffolding. Scene ownership/isolation is not enforced consistently.
- `[ ]` Add Alembic migrations.
- `[x]` Add benchmark JSON schema.
- `[~]` Add backend gating/upload/auth tests; complete success-path and scene-isolation integration coverage remains open. Tests have not been run as part of this status review.
- `[ ]` Add frontend smoke test for dashboard/viewer.
- `[x]` Fix hardcoded accuracy defaults — show "---" when no eval data available.

## Module 6: Accuracy Honesty
- `[x]` Add a fixed-configuration held-out real-device benchmark runner and report schema; no qualifying manifest/ground-truth set exists yet, so no pilot score is available.
- `[ ]` Calibrate poseToStatus thresholds against real validation data (correlate confidence/inliers vs measured translation error).
- `[ ]` Add real-time translation-error estimate to VPS pose response (not just confidence proxy).
- `[ ]` Display per-frame accuracy estimate in navigatus AR view.
- `[ ]` Document validation methodology and expected accuracy range per scene type.

## Module 4: SDK And Developer Experience
- `[x]` Add API-key support to the Unity REST VPS client; this does not make a key embedded in a distributed client confidential.
- `[x]` Add Unity quickstart.
- `[~]` Add sample localization scripts/docs; a runnable Unity sample scene/project and verified integration remain open.
- `[x]` Document coordinate conversion.
- `[x]` Document localization confidence/error handling.

## Module 5: Commercial Execution
- `[ ]` Build target list of 50 accounts.
- `[ ]` Complete 10 discovery calls.
- `[ ]` Send 3 pilot proposals.
- `[ ]` Close 1 paid pilot or LOI by day 30 target.
- `[ ]` Close 2-3 paid pilots or one annual/expanded conversion by day 90 target.
