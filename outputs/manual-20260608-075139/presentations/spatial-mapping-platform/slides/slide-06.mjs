import { C, bg, kicker, title, footer, metric, stage, rule } from "./common.mjs";

export async function slide06(presentation, ctx) {
  const slide = presentation.slides.add();
  bg(slide, ctx);
  kicker(slide, ctx, "EVIDENCE TO SHOW NOW");
  title(slide, ctx, "The MVP proves the full loop; pilot metrics need one confirmed benchmark set.", { w: 930, size: 42 });

  metric(slide, ctx, "Implemented", "scene upload, process queue, frames, anchors, tiles", 72, 178, 318, { valueColor: C.ink });
  metric(slide, ctx, "Implemented", "VPS localize API with pose, confidence, inliers", 482, 178, 318, { valueColor: C.cyan });
  metric(slide, ctx, "Implemented", "Unity client path for camera-frame localization", 892, 178, 318, { valueColor: C.lime });

  stage(slide, ctx, "Proof objects already in repo", "FastAPI routes, Celery processing task, COLMAP/Splatting services, FAISS localization path, 3D viewer managers, anchor persistence, WebSocket agent sync, Unity SDK package.", 72, 338, 548, 178, { fill: C.white });
  stage(slide, ctx, "Metric caveat before client use", "Current materials contain mixed values: 4.1cm in docs/UI examples, 12cm in mock dashboard data, and broader language such as sub-decimeter. The deck should use final numbers only after one evaluation report is selected.", 662, 338, 548, 178, { fill: "#FFF3ED", line: "#F0C2B0", color: C.rust });

  rule(slide, ctx, 72, 570, 1138, C.ink, 2);
  ctx.addText(slide, { text: "Recommended client wording: 'pilot-grade localization with measured pose confidence' until final accuracy data is locked.", x: 72, y: 588, w: 980, h: 54, fontSize: 22, bold: true, color: C.ink, typeface: ctx.fonts.title, insets: { left: 0, right: 0, top: 0, bottom: 0 } });
  footer(slide, ctx, "Sources: validation_report_agent_4.md; docs/api_contract.md; frontend/lib/api.ts; frontend/app/page.tsx");
  return slide;
}
