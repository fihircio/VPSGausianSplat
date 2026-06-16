import { C, bg, kicker, title, body, footer, chip, metric, rule } from "./common.mjs";

export async function slide01(presentation, ctx) {
  const slide = presentation.slides.add();
  bg(slide, ctx, C.ink);
  kicker(slide, ctx, "CLIENT PITCH / SPATIAL MAPPING PLATFORM", { textColor: "#B8C2CF" });
  title(slide, ctx, "Turn spaces into reusable AR-ready maps.", { y: 104, w: 690, h: 172, size: 58, color: C.white });
  body(slide, ctx, "A web-first platform for scanning environments, reconstructing photorealistic 3D maps, localizing devices, and anchoring persistent digital content.", { y: 318, w: 650, h: 92, size: 21, color: "#C6CED8" });

  const chips = ["Scan", "Reconstruct", "Visualize", "Localize", "Anchor", "Deploy"];
  rule(slide, ctx, 90, 474, 720, "#2F4658", 2);
  chips.forEach((c, i) => chip(slide, ctx, c, 72 + i * 126, 456, 108, { fill: i < 3 ? "#1A2A38" : "#162B33", line: "#2F4658", color: i < 3 ? C.lime : C.cyan, size: 12 }));

  metric(slide, ctx, "Open API", "client apps localize against reusable maps", 820, 132, 300, { fill: "#172331", line: "#2F4658", valueColor: C.lime, labelColor: "#B8C2CF" });
  metric(slide, ctx, "6DoF pose", "position, rotation, confidence, inliers", 820, 252, 300, { fill: "#172331", line: "#2F4658", valueColor: C.cyan, labelColor: "#B8C2CF" });
  metric(slide, ctx, "3D viewer", "Gaussian Splat / point-cloud scene layer", 820, 372, 300, { fill: "#172331", line: "#2F4658", valueColor: C.white, labelColor: "#B8C2CF" });

  footer(slide, ctx, "Sources: README.md; docs/demo_walkthrough.md; frontend/app/*; backend/api/*", true);
  return slide;
}
