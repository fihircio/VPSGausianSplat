# Roadmap Checklist: Phase 5 (Commercialization And Google 3D Data)

This checklist tracks the 90-day commercialization objective: turn the current VPS + Gaussian Splatting MVP into a pilot-ready commercial product, while using Google 3D as a synthetic training and evaluation source.

## Module 1: Commercial Pilot Package
- `[x]` Create customer-facing one-page pilot offer.
- `[x]` Create pilot proposal template.
- `[x]` Create pilot success metric template.
- `[x]` Create security/privacy FAQ.
- `[ ]` Record 2-minute demo video.
- `[x]` Create 3-package pricing sheet: Pilot, Venue, Network.

## Module 2: Google 3D Synthetic Data Engine
- `[x]` Document permission metadata record.
- `[x]` Select 3 AOIs: dense urban, storefront, low-texture/open.
- `[x]` Implement AOI tile/source manifest ingestion.
- `[x]` Implement WGS84/ECEF/ENU coordinate utilities.
- `[x]` Generate deterministic synthetic camera paths.
- `[x]` Render 10,000 RGB+pose frames for first AOI (KLCC: 10,000 frames, 306 MB, procedural render).
- `[x]` Run baseline feature benchmark across at least two feature modes (ORB vs SIFT on 500 sampled frames).
- `[x]` Complete synthetic-to-real transfer check (baseline script built, cross-domain eval run: transfer gap ~0.17; needs matched-location field capture for definitive result).

## Module 3: Pilot-Ready Engineering
- `[x]` Remove hardcoded localhost URLs from frontend, Navigatus, and Unity SDK.
- `[x]` Add upload size/type validation.
- `[x]` Gate destructive and debug endpoints.
- `[x]` Add API key auth for localization and scene APIs.
- `[x]` Add tenant/project ownership model.
- `[ ]` Add Alembic migrations.
- `[x]` Add benchmark JSON schema.
- `[x]` Add backend tests for upload/process/localize/auth.
- `[ ]` Add frontend smoke test for dashboard/viewer.
- `[x]` Fix hardcoded accuracy defaults — show "---" when no eval data available.

## Module 6: Accuracy Honesty
- `[ ]` Calibrate poseToStatus thresholds against real validation data (correlate confidence/inliers vs measured translation error).
- `[ ]` Add real-time translation-error estimate to VPS pose response (not just confidence proxy).
- `[ ]` Display per-frame accuracy estimate in navigatus AR view.
- `[ ]` Document validation methodology and expected accuracy range per scene type.

## Module 4: SDK And Developer Experience
- `[ ]` Add Unity SDK API key support.
- `[x]` Add Unity quickstart.
- `[ ]` Add sample scene or sample localization flow.
- `[x]` Document coordinate conversion.
- `[x]` Document localization confidence/error handling.

## Module 5: Commercial Execution
- `[ ]` Build target list of 50 accounts.
- `[ ]` Complete 10 discovery calls.
- `[ ]` Send 3 pilot proposals.
- `[ ]` Close 1 paid pilot or LOI by day 30 target.
- `[ ]` Close 2-3 paid pilots or one annual/expanded conversion by day 90 target.
