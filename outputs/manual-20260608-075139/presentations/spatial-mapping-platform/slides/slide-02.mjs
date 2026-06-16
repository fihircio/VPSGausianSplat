import { C, bg, kicker, title, body, footer, stage, rule } from "./common.mjs";

export async function slide02(presentation, ctx) {
  const slide = presentation.slides.add();
  bg(slide, ctx);
  kicker(slide, ctx, "THE MARKET GAP");
  title(slide, ctx, "Spatial experiences still break between capture, mapping, and deployment.", { w: 900, size: 46 });
  body(slide, ctx, "Most teams can create a scan or an AR prototype. The hard part is turning that scan into a reusable positioning layer that many apps can trust.", { y: 176, w: 660, size: 22 });

  stage(slide, ctx, "Closed VPS stacks", "Accurate services exist, but buyers often inherit platform lock-in, limited map control, and constrained deployment paths.", 72, 330, 330, 170, { line: "#CFC7B8" });
  stage(slide, ctx, "Fragmented 3D tools", "Capture, reconstruction, hosting, and AR anchoring are usually separate workflows with handoff loss between each tool.", 474, 330, 330, 170, { line: "#CFC7B8" });
  stage(slide, ctx, "Manual alignment tax", "Agencies and app teams spend pilot time re-aligning content instead of building durable spatial experiences.", 876, 330, 330, 170, { line: "#CFC7B8" });

  rule(slide, ctx, 72, 548, 1134, C.ink, 2);
  ctx.addText(slide, { text: "Client need: one controlled map pipeline that makes the physical site reusable across AR, navigation, visualization, and operations.", x: 72, y: 570, w: 980, h: 54, fontSize: 24, bold: true, color: C.ink, typeface: ctx.fonts.title, insets: { left: 0, right: 0, top: 0, bottom: 0 } });
  footer(slide, ctx, "Sources: idea.md; VPSGausianSplat vs. Multiset.ai gap analysis");
  return slide;
}
