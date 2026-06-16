import { C, bg, kicker, title, body, footer, stage, rule } from "./common.mjs";

export async function slide05(presentation, ctx) {
  const slide = presentation.slides.add();
  bg(slide, ctx);
  kicker(slide, ctx, "CLIENT DEMO FLOW");
  title(slide, ctx, "A pilot can be shown as one continuous operating journey.", { w: 760, h: 92, size: 42 });
  body(slide, ctx, "This flow is designed for non-technical buyers while still exposing the technical proof needed by implementation teams.", { y: 178, w: 720, h: 70 });

  const steps = [
    ["Upload site scan", "A walkthrough video becomes a named scene in the portal."],
    ["Monitor processing", "Progress surfaces frame extraction, SfM reconstruction, splat generation, and VPS indexing."],
    ["Inspect 3D map", "The viewer loads Gaussian Splat or fallback point-cloud data with camera poses."],
    ["Test positioning", "A query image returns 6DoF pose, confidence, and inlier count."],
    ["Place anchors", "Persistent GLB/object anchors are stored against scene coordinates."]
  ];
  steps.forEach((s, i) => {
    const y = 292 + i * 62;
    ctx.addText(slide, { text: String(i + 1).padStart(2, "0"), x: 92, y: y + 7, w: 44, h: 26, fontSize: 20, bold: true, color: i === 3 ? C.cyan : C.lime, typeface: ctx.fonts.mono, insets: { left: 0, right: 0, top: 0, bottom: 0 } });
    rule(slide, ctx, 150, y + 23, 90, i === 3 ? C.cyan : C.line, 2);
    stage(slide, ctx, s[0], s[1], 260, y, 760, 56, { fill: i === 3 ? "#E8FBFD" : C.white, line: i === 3 ? C.cyan : C.line, labelSize: 15, labelH: 18, detailSize: 11, detailY: 34, detailH: 16 });
  });

  stage(slide, ctx, "Pilot outcome", "A client leaves the demo with a reusable site map, working localization endpoint, and a clear integration path for AR or spatial operations.", 898, 126, 262, 126, { fill: C.ink, line: C.ink, color: C.lime, detailColor: "#C6CED8", labelSize: 17, detailSize: 11 });
  footer(slide, ctx, "Sources: docs/demo_walkthrough.md; frontend/app/upload; frontend/app/scenes; frontend/app/localize; viewer page");
  return slide;
}
