# Pilot Success Metric Template

This template is completed at pilot kickoff. Agree the evaluation protocol and fill the **Baseline** and **Target** columns before collecting held-out evaluation data; fill **Actual** and **Pass?** at closeout. The blank target cells are intentional: the project has no universal, independently validated performance threshold. Do not use this template to imply a guaranteed result.

---

## 1. Technical Success Metrics

| Metric | Baseline | Target | Actual | Pass? |
|---|---|---|---|---|
| Localization success rate | — | Customer-agreed: | | |
| Median translation error (m) | — | Customer-agreed: | | |
| P95 translation error (m) | — | Customer-agreed: | | |
| Median rotation error (°) | — | Customer-agreed: | | |
| Time to first localization (s) | — | Customer-agreed: | | |
| Localization latency (ms) | — | Customer-agreed: | | |
| Processing turnaround | — | Customer-agreed: | | |
| Map coverage of agreed pilot area | — | Customer-agreed: | | |

**Notes on thresholds:**

- Define a localized query and the success/error bounds before the evaluation; report the numerator, denominator, and excluded samples.
- Translation and rotation error require appropriate ground truth. If it is missing or insufficient, mark the metric “not measured”; confidence or inlier counts are not substitutes for position error.
- Keep setup/tuning data separate from held-out evaluation queries and do not tune against the held-out results.
- Record device, scene, lighting, capture date, sample count, ground-truth method, and failure categories. Report synthetic benchmark results separately from real-device site results.

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
