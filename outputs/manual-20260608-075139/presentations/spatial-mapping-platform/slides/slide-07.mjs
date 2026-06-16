import { C, bg, kicker, title, body, footer, stage } from "./common.mjs";

export async function slide07(presentation, ctx) {
  const slide = presentation.slides.add();
  bg(slide, ctx);
  kicker(slide, ctx, "USE-CASE SURFACE");
  title(slide, ctx, "The same spatial map can support multiple high-value verticals.", { w: 880, size: 44 });
  body(slide, ctx, "Keep the platform general. Sell the first client a focused pilot, then expand the reusable map into adjacent workflows.", { y: 174, w: 720 });

  const uses = [
    ["Retail and malls", "store navigation, campaign AR, product discovery", C.lime],
    ["Events and exhibitions", "booth wayfinding, shared AR moments, sponsor overlays", C.cyan],
    ["Property and tourism", "digital twins, guided tours, persistent content", "#CFA7FF"],
    ["Industrial sites", "maintenance overlays, safety zones, asset localization", "#F3C969"],
    ["Healthcare campuses", "indoor wayfinding, staff coordination, room-level context", C.rust],
  ];
  uses.forEach((u, i) => {
    const x = i < 3 ? 72 + i * 376 : 260 + (i - 3) * 438;
    const y = i < 3 ? 300 : 472;
    stage(slide, ctx, u[0], u[1], x, y, i < 3 ? 310 : 360, 112, { fill: C.white, line: u[2], color: u[2], labelSize: 18, detailSize: 13 });
  });

  footer(slide, ctx, "Sources: idea.md customer segments; current frontend healthcare example treated as one vertical, not the platform identity");
  return slide;
}
