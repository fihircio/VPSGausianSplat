import { C, bg, kicker, title, body, footer, stage, chip } from "./common.mjs";

export async function slide09(presentation, ctx) {
  const slide = presentation.slides.add();
  bg(slide, ctx);
  kicker(slide, ctx, "PILOT OFFER");
  title(slide, ctx, "Package the client ask as a bounded spatial-map pilot.", { w: 840, size: 46 });
  body(slide, ctx, "The first sale should not promise a complete enterprise AR cloud. It should prove one site, one map, one localization loop, and one client integration path.", { y: 174, w: 720 });

  stage(slide, ctx, "1. Site capture", "Client selects one floor, venue zone, showroom, or outdoor pocket. Team records guided phone scan and reference query images.", 72, 304, 350, 152, { fill: C.white });
  stage(slide, ctx, "2. Map build", "Process scene, produce 3D visual layer, build feature index, define coordinate conventions, and save initial anchors.", 466, 304, 350, 152, { fill: C.white });
  stage(slide, ctx, "3. Validation", "Run localization test set, report success rate, translation error, confidence, inliers, and known failure cases.", 860, 304, 350, 152, { fill: C.white });

  chip(slide, ctx, "Deliverables: hosted scene, API access, 3D viewer, localization report, Unity integration notes", 72, 536, 734, { fill: C.ink, line: C.ink, color: C.white });
  chip(slide, ctx, "Decision gate: expand to more maps only after measured pilot accuracy is accepted", 836, 536, 374, { fill: "#FFF3ED", line: "#F0C2B0", color: C.rust });
  footer(slide, ctx, "Sources: docs/demo_walkthrough.md; docs/api_contract.md; validation_report_agent_4.md");
  return slide;
}
