# Visual Positioning Pilot

## Test one real use case in one bounded area

We work with a venue or facility team to evaluate whether visual positioning can support a specific navigation or persistent-AR experience in a defined space. The pilot is a supported technical evaluation with agreed measurements; it is not a promise of building-wide coverage or a production service-level agreement.

```text
agree the area and use case -> prepare a map -> localize real device frames -> place a small set of anchors -> report results
```

## Best fit

- A museum, gallery, showroom, campus, or other venue with a clear indoor/outdoor pilot area.
- An AR agency with a named end-customer and an approved place to evaluate.
- A team that can provide site access, an operational contact, and representative devices or capture sessions.

The first engagement should have one decision-maker, one technical contact, and one measurable user scenario.

## Pilot scope

Included, subject to technical and site-readiness review:

- One route or zone with boundaries agreed before kickoff.
- Map preparation using an input path confirmed for the specific site during technical discovery.
- Access to the current web portal and localization API for the agreed evaluation.
- One supported demo path using either Navigatus or the Unity REST client.
- Up to three persistent anchors in the agreed area.
- A report of localization outcomes on an agreed real-device sample, including failures and limitations.
- A closeout review with a go, conditional-go, or no-go recommendation.

The pilot does not include a guarantee that a site will meet its target, full-building mapping, production hosting, a production SLA, cross-customer tenancy, a dedicated mobile capture app, object recognition/tracking, or broad scanner-format support. We confirm supported inputs, deployment, and data-handling terms in writing before accepting site data.

## Schedule and working model

Typical planning window: four to six weeks after access, input format, and evaluation criteria are agreed. The schedule may change if site access, data quality, processing, or integration work is delayed.

| Stage | Work | Decision/output |
|---|---|---|
| Scope | Agree user scenario, boundaries, devices, capture permissions, and metrics | Signed pilot brief and data-handling plan |
| Readiness | Review representative data and confirm the supported ingestion path | Go/no-go on map preparation |
| Demo | Prepare the map, configure the chosen demo client, and place anchors | Demonstration in the agreed area |
| Evaluation | Collect held-out real-device queries and record outcomes | Results with sample size, conditions, and failure categories |
| Closeout | Review results and operational gaps | Go, conditional-go, or no-go recommendation |

## Acceptance measures

Targets are selected with the customer before kickoff and depend on the use case. The report should include at least localization success rate, median and p95 translation error where ground truth is available, rotation error where available, time to first localization, latency, test conditions, and failure categories. If ground truth or enough representative samples are unavailable, report those metrics as unavailable rather than substituting confidence scores or synthetic results.

Synthetic or third-party data results are kept separate from the real-device pilot results. They do not prove performance in the customer's environment.

## Customer responsibilities

- Identify the business owner, technical contact, and intended users.
- Approve access to the bounded area and permission for any required capture or recording.
- Provide site constraints, representative devices, and a contact to coordinate evaluation sessions.
- Review the proposed data inputs, retention/deletion terms, and deployment approach before sharing data.
- Agree evaluation targets and attend a weekly status review and closeout.

## Support and commercial hypothesis

The pilot is delivered as a time-bounded, founder/engineering-supported engagement through an agreed contact and scheduled working sessions. Support is best-effort during agreed business hours; response times and uptime are not guaranteed unless separately contracted. Production hosting and ongoing operations require separate technical and commercial review.

Initial pricing hypotheses for discovery conversations only:

- Small, single-zone evaluation: **USD 8,000–15,000**.
- More complex facility evaluation: **USD 20,000–40,000**, subject to scope.

These ranges have not been validated through paid customer deals. A fixed quote should follow site, data, integration, and support scoping. No automatic annual-conversion credit is implied; any credit must appear in the signed proposal.

## Next step

A 30-minute discovery call to confirm the problem, site access, data path, buyer, and whether a bounded technical evaluation is appropriate.
