import { C, bg, kicker, title, footer, stage, rule } from "./common.mjs";

export async function slide10(presentation, ctx) {
  const slide = presentation.slides.add();
  bg(slide, ctx, C.ink);
  kicker(slide, ctx, "ROADMAP", { textColor: "#B8C2CF" });
  title(slide, ctx, "From MVP pipeline to production spatial cloud.", { w: 820, size: 50, color: C.white });

  const phases = [
    ["Now: full-loop MVP", "Upload, process, visualize, localize, anchor, Unity client path.\nUse for controlled demos and scoped pilots.", C.lime],
    ["Next: pilot hardening", "Single source of truth for metrics, robust capture protocol, mobile touch viewer, splat format conversion, evaluation reports.", C.cyan],
    ["Scale: enterprise maps", "Deep features, LiDAR/E57 ingestion, map stitching, cloud object storage, SDK background localization, multi-map operations.", "#F3C969"],
  ];
  phases.forEach((p, i) => {
    const x = 72 + i * 390;
    stage(slide, ctx, p[0], p[1], x, 238, 320, 230, { fill: "#172331", line: p[2], color: p[2], detailColor: "#C6CED8", labelSize: 20, detailSize: 14 });
    if (i < 2) {
      rule(slide, ctx, x + 320, 350, 70, "#465869", 2);
      ctx.addText(slide, { text: ">", x: x + 352, y: 337, w: 22, h: 22, fontSize: 18, bold: true, color: "#718296", insets: { left: 0, right: 0, top: 0, bottom: 0 } });
    }
  });

  ctx.addText(slide, { text: "Client-facing narrative: start with one valuable physical space, prove reliable localization, then expand the map library.", x: 72, y: 552, w: 940, h: 58, fontSize: 25, bold: true, color: C.white, typeface: ctx.fonts.title, insets: { left: 0, right: 0, top: 0, bottom: 0 } });
  footer(slide, ctx, "Sources: docs/roadmap_checklist.md; validation_report_agent_4.md; gap analysis roadmap", true);
  return slide;
}
