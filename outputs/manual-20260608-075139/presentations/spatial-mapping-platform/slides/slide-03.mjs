import { C, bg, kicker, title, footer, stage, chip, rule } from "./common.mjs";

export async function slide03(presentation, ctx) {
  const slide = presentation.slides.add();
  bg(slide, ctx);
  kicker(slide, ctx, "PRODUCT LOOP");
  title(slide, ctx, "The platform turns a site walkthrough into a reusable spatial service.", { w: 860, size: 44 });

  const y = 250;
  const items = [
    ["01 Scan", "Phone video or image set from the physical site."],
    ["02 Process", "Frame extraction, COLMAP SfM, splat / PLY output."],
    ["03 Index", "Feature descriptors stored in FAISS for retrieval."],
    ["04 Localize", "Query image returns pose, confidence, and inliers."],
    ["05 Anchor", "Persistent objects saved against map coordinates."],
    ["06 Deploy", "Unity / API clients reuse the same spatial map."]
  ];
  items.forEach((item, i) => {
    const x = 72 + i * 190;
    stage(slide, ctx, item[0], item[1], x, y + (i % 2) * 74, 154, 136, { fill: i === 3 ? "#E8FBFD" : C.white, line: i === 3 ? C.cyan : C.line, labelSize: 16, detailSize: 12 });
    if (i < items.length - 1) {
      rule(slide, ctx, x + 154, y + 60 + (i % 2) * 74, 36, i === 2 ? C.cyan : "#B8B1A5", 2);
      ctx.addText(slide, { text: ">", x: x + 172, y: y + 47 + (i % 2) * 74, w: 20, h: 20, fontSize: 18, bold: true, color: i === 2 ? C.cyan : "#B8B1A5", insets: { left: 0, right: 0, top: 0, bottom: 0 } });
    }
  });

  chip(slide, ctx, "Core MVP: scan -> process -> visualize -> localize", 72, 560, 420, { fill: C.ink, line: C.ink, color: C.lime });
  chip(slide, ctx, "Client value: one map can support many spatial apps", 520, 560, 444, { fill: C.ink, line: C.ink, color: C.white });
  footer(slide, ctx, "Sources: README.md; docs/demo_walkthrough.md; backend/workers/tasks.py; backend/services/vps.py");
  return slide;
}
