import { C, bg, kicker, title, footer, stage, rule } from "./common.mjs";

export async function slide08(presentation, ctx) {
  const slide = presentation.slides.add();
  bg(slide, ctx);
  kicker(slide, ctx, "POSITIONING");
  title(slide, ctx, "The wedge is an open, controllable alternative to closed spatial stacks.", { w: 880, size: 44 });

  const rows = [
    ["Open map ownership", "Client controls site scans, scene IDs, anchors, and API access.", "Differentiates from closed ecosystem VPS."],
    ["Photorealistic scene layer", "Gaussian Splat / PLY output gives teams a visual map, not only coordinates.", "Bridges 3D capture and AR deployment."],
    ["VPS as a service", "Query images return pose, rotation, confidence, and inliers.", "Makes the physical site reusable by multiple apps."],
    ["SDK-ready integration", "Unity package aligns MapSpace to localized camera pose.", "Shortens path from pilot to application."],
  ];
  rows.forEach((r, i) => {
    const y = 182 + i * 92;
    ctx.addText(slide, { text: r[0], x: 86, y: y + 8, w: 260, h: 30, fontSize: 19, bold: true, color: C.ink, typeface: ctx.fonts.title, insets: { left: 0, right: 0, top: 0, bottom: 0 } });
    stage(slide, ctx, "Platform capability", r[1], 390, y, 360, 76, { fill: i % 2 === 0 ? C.white : "#FBFAF6", line: C.line, color: C.lime, labelSize: 12, labelH: 16, detailSize: 12, detailY: 34, detailH: 28 });
    stage(slide, ctx, "Client outcome", r[2], 800, y, 360, 76, { fill: i % 2 === 0 ? "#E8FBFD" : C.white, line: C.cyan, color: C.cyan, labelSize: 12, labelH: 16, detailSize: 12, detailY: 34, detailH: 28 });
    rule(slide, ctx, 750, y + 32, 50, C.line, 2);
  });

  footer(slide, ctx, "Sources: gap analysis; README.md; docs/api_contract.md; Unity SDK MapSpace/VPSClient");
  return slide;
}
