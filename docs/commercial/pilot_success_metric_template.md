# Pilot Success Metric Template

This template is filled out at the start of each pilot to lock measurable success gates. Complete the **Baseline** and **Target** columns before kickoff. Fill **Actual** and **Pass?** at pilot close.

---

## 1. Technical Success Metrics

| Metric | Baseline | Target | Actual | Pass? |
|---|---|---|---|---|
| Localization success rate | — | ≥ 0.70 | | |
| Median translation error (m) | — | < 0.30 m | | |
| P95 translation error (m) | — | < 0.80 m | | |
| Median rotation error (°) | — | < 8° | | |
| Time to first localization (s) | — | < 4 s | | |
| Average inliers per query frame | — | > 30 | | |
| Average localization confidence | — | > 0.50 | | |
| Scene processing turnaround | — | < 30 min per floor | | |
| Map coverage of agreed pilot area | — | ≥ 90 % | | |

**Notes on thresholds:**

- `success_rate ≥ 0.70` means at least 7 out of 10 representative test frames localize within the error bounds above.
- `translation_error < 0.30 m` is the recommended production target. Accept `< 0.50 m` for Pilot tier.
- Synthetic Google 3D benchmark results are not substitutes for real-device validation. All figures above apply to real device capture on the target site.

---

## 2. Commercial Success Metrics

| Metric | Target | Actual | Pass? |
|---|---|---|---|
| Customer demo accepted | Yes | | |
| Customer rated demo ≥ 3/5 | Yes | | |
| Rollout decision made within 2 weeks of final demo | Yes | | |
| Expansion area or second-site discussion initiated | Yes | | |
| Budget owner identified for post-pilot contract | Yes | | |
| No critical support issues during pilot delivery | Yes | | |

---

## 3. Pilot Success Gate Summary

| Gate | Status |
|---|---|
| Technical: success_rate target met | ☐ Pass / ☐ Fail |
| Technical: translation error target met | ☐ Pass / ☐ Fail |
| Technical: rotation error target met | ☐ Pass / ☐ Fail |
| Commercial: demo acceptance | ☐ Pass / ☐ Fail |
| Commercial: rollout decision on track | ☐ Pass / ☐ Fail |

---

## 4. Overall Pilot Verdict

- `[ ]` **GO** — All gates passed. Proceed to proposal for rollout / annual / expansion contract.
- `[ ]` **CONDITIONAL GO** — Most gates passed but one metric missed. Agree on remediation within 2 weeks before full commitment.
- `[ ]` **NO-GO** — Multiple gates failed. Deliver findings report, recommend whether a second pilot with amended scope is viable.

---

## 5. Pilot Metadata

| Field | Value |
|---|---|
| Customer | |
| Site / Location | |
| Pilot area | |
| Pilot start date | |
| Pilot end date | |
| Evaluation date | |
| Evaluated by | |
| Scene ID(s) used | |
| Device(s) used for validation | |
| Feature mode used (ORB / SuperPoint) | |
| Storage backend | LOCAL / S3 / AZURE |

---

## 6. Failure Notes

If any gate failed, document:

- Root cause:
- Attempted remediation:
- Customer reaction:
- Recommended next step:
