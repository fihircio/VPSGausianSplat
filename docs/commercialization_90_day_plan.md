# 90-Day Commercialization Plan

## Objective

Convert the current VPS + Gaussian Splatting MVP into a pilot-ready commercial product within 90 days.

The goal is not full self-serve SaaS. The goal is to close and deliver paid pilots that prove a repeatable wedge:

```text
map a space -> localize device camera -> place persistent AR anchors -> validate accuracy -> expand to paid deployment
```

## Product Position

We are building a spatial infrastructure platform for private and semi-private spaces where normal GPS is weak or unusable.

Initial commercial wedge:

- Indoor and campus wayfinding.
- Venue AR experiences.
- Facility digital twin plus spatial anchoring.
- Unity/WebAR developers who need persistent real-world positioning.

Google 3D is a synthetic data acceleration layer. It helps us pretrain, benchmark, and create outdoor demos faster. It does not replace real phone validation for paid customer claims.

## Core Commercial Offer

### Paid Pilot Package

Scope:

- One zone, route, floor, or outdoor AOI.
- VPS map or synthetic/demo map generation.
- Web portal access.
- Localization API.
- Unity SDK or Navigatus demo integration.
- Anchor placement.
- Accuracy and reliability report.

Duration:

- 4-6 weeks after site/data access.

Pricing hypothesis:

- Small venue pilot: USD 8k-15k.
- Enterprise or complex facility pilot: USD 20k-40k.
- Credit part of the pilot fee toward an annual contract if they convert quickly.

Success promise:

> We will prove whether your space can support reliable visual positioning and deliver one production-shaped spatial experience.

Do not promise:

- Full-building coverage.
- Perfect centimeter accuracy.
- Unlimited scale.
- Consumer-grade SLA.
- Fully autonomous self-serve scanning.

## Ideal Customer Profile

Best first customers:

- Museums, galleries, immersive venues.
- Retail destinations and showrooms.
- Campuses and hospitals with wayfinding pain.
- AR agencies building client activations.
- Property developers with demo centers.

Buyer profile:

- Innovation, digital experience, operations, or facilities lead.
- Owns a physical venue.
- Can give capture/site/data access.
- Has budget for pilots.
- Can decide within 30-45 days.

Avoid for first 90 days:

- Large public-sector RFPs.
- Safety-critical industrial deployments.
- Full airport-scale rollouts.
- Buyers requiring heavy compliance before a small pilot.

## Strategic Pillars

### 1. Pilot Reliability

The demo must work repeatedly.

Deliverables:

- Stable local and hosted demo path.
- Seeded scene or dataset.
- Clear runbook.
- Reliable upload/process/view/localize loop.
- Controlled fallback path if live processing fails.

### 2. Measured Accuracy

Commercial trust depends on measured performance, not claims.

Deliverables:

- Benchmark report template.
- Real-device validation checklist.
- Synthetic Google 3D benchmark report.
- Accuracy language that separates synthetic, lab, and real-site results.

### 3. Google 3D Data Engine

Use Google 3D to accelerate training and outdoor demos.

Deliverables:

- AOI registry.
- Tile/source manifest.
- WGS84/ECEF/ENU transform utilities.
- Synthetic camera path generation.
- RGB+pose render dataset.
- Feature/matcher benchmark.

### 4. SDK And Developer Experience

The platform becomes valuable when a developer can integrate it quickly.

Deliverables:

- Unity SDK quickstart.
- API key support.
- One working sample scene.
- Clear coordinate conversion explanation.
- Error handling and localization confidence guide.

### 5. Commercial Packaging

Founder-led sales needs simple assets.

Deliverables:

- One-page pilot offer.
- 8-slide pitch deck.
- 2-minute demo video.
- Pilot proposal template.
- Security/privacy FAQ.
- Post-pilot rollout pricing sheet.

## 0-30 Days: Prove The Machine Can Run

### Commercial

- Pick one primary wedge for outreach.
- Build a target list of 50 accounts.
- Run at least 30 qualified outreach attempts.
- Complete 10 discovery calls.
- Send 3 pilot proposals.
- Aim for 1 signed pilot or strong LOI.

### Product

- Make demo path deterministic.
- Remove or qualify unsupported accuracy claims.
- Write customer-facing pilot scope.
- Define pilot success metrics:
  - localization success rate,
  - median relocalization time,
  - median/p95 position error,
  - rotation error,
  - processing turnaround,
  - customer demo acceptance.

### Engineering

- Fix hardcoded localhost URLs.
- Add environment-based API and WebSocket base URLs.
- Add upload size/type validation.
- Gate destructive endpoints.
- Start API key authentication design.
- Add benchmark JSON schema.

### Google 3D

- Confirm permission metadata.
- Choose 3 AOIs.
- Implement first AOI manifest ingestion.
- Validate WGS84/ECEF/ENU conversion.
- Render first 10,000 RGB+pose frames.
- Produce first ORB/SIFT or feature baseline report.

### Exit Gates

- One complete demo can be run from a clean state.
- One Google 3D AOI has a dataset manifest and rendered frames.
- One benchmark report exists.
- One pilot offer is ready to send.
- At least one serious commercial conversation is active.

## 31-60 Days: Deliver First Pilot Shape

### Commercial

- Deliver or actively implement first paid pilot.
- Continue outreach while building.
- Send 2 additional proposals.
- Validate pricing in live conversations.
- Draft post-pilot annual options.

### Product

- Produce pilot result report template.
- Add readiness checklist for a scene/map.
- Add customer-safe status/error states.
- Package Navigatus or Unity demo around one use case.

### Engineering

- Add API key auth for backend and SDK.
- Add basic tenant/project ownership model.
- Add Alembic migrations before schema expansion.
- Make S3/Azure storage path tenant/project scoped.
- Add pytest coverage for auth, scene isolation, upload, process, localize.
- Add frontend smoke test for dashboard/viewer.

### Google 3D

- Scale from 1 AOI to 3 AOIs.
- Add deterministic camera policies:
  - pedestrian,
  - storefront,
  - intersection,
  - hard negatives.
- Add held-out query/reference split.
- Compare at least two feature modes.
- Run synthetic-to-real check if field sample is available.

### Exit Gates

- First pilot is delivered or on track.
- Authenticated API path works for at least localization.
- Synthetic dataset benchmark is repeatable.
- Demo can run without manual code edits.
- Customer proposal and report templates are ready.

## 61-90 Days: Convert And Repeat

### Commercial

- Push first pilot toward one of:
  - annual license,
  - expanded pilot,
  - second site,
  - partner introduction.
- Close 2-3 paid pilots total, or 1 pilot plus annual conversion.
- Create 3-package pricing:
  - Pilot,
  - Venue,
  - Network.
- Identify the strongest ICP by actual sales pull.

### Product

- Publish SDK quickstart.
- Create case study from first pilot if permitted.
- Create partner one-pager for AR agencies/integrators.
- Define product roadmap from repeated buyer blockers.

### Engineering

- Add observability:
  - request IDs,
  - localization latency,
  - confidence distribution,
  - worker phase timing,
  - API key usage.
- Harden WebSocket sync with auth and rate limits.
- Add worker job table with retry/cancellation/error categories.
- Add seeded demo reset script.
- Add CI gates for backend import/tests and frontend build.

### Google 3D

- Decide whether to scale to 25 AOIs.
- Define if Google 3D is:
  - pretraining only,
  - benchmark plus pretraining,
  - outdoor production initialization.
- Package outdoor demo dataset if useful for sales.
- Compare synthetic-only, real-only, and synthetic-pretrain plus real fine-tune.

### Exit Gates

- 2-3 paid pilots signed or 1 conversion to annual/expanded deployment.
- One ICP clearly outperforms others.
- One repeatable demo and deployment flow exists.
- One benchmark pipeline is reproducible.
- One SDK integration path is documented and tested.

## Weekly Operating Rhythm

- 2 days selling and customer development.
- 2 days engineering and pilot delivery.
- 0.5 day benchmark/data validation.
- 0.5 day packaging, docs, proposals, and metrics review.

Every Friday, update:

- Sales pipeline.
- Pilot delivery status.
- Engineering blockers.
- Benchmark results.
- Next week top 3 priorities.

## KPIs

Commercial:

- Qualified accounts contacted.
- Discovery calls completed.
- Pilot proposals sent.
- Signed pilots.
- Pilot-to-expansion conversations.

Technical:

- Localization success rate.
- Median and p95 translation error.
- Median rotation error.
- Time to first localization.
- Processing turnaround time.
- API/localization latency.
- Synthetic-to-real transfer score.

Operational:

- Demo setup time.
- Number of manual steps.
- Failed processing jobs.
- Support issues per pilot.

## What Not To Build Yet

- Full self-serve SaaS onboarding.
- Billing system.
- Marketplace.
- No-code AR editor.
- Native iOS/Android SDKs unless a signed pilot requires them.
- Multi-site enterprise console.
- Broad engine support beyond Unity/Web.
- Large-scale map stitching before one customer pays for it.

## Decision Rules

Build only if one of these is true:

- It blocks a signed pilot.
- It reduces demo/pilot failure risk.
- It improves measurable localization performance.
- It creates a sales asset needed for active deals.
- It is required to use Google 3D data safely and repeatably.

Defer if:

- It is mainly platform polish.
- It serves a hypothetical future customer.
- It expands scope without increasing pilot close probability.
- It cannot be measured within the 90-day window.
