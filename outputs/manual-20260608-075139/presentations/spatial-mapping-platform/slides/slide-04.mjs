import { C, bg, kicker, title, footer, stage, rule } from "./common.mjs";

export async function slide04(presentation, ctx) {
  const slide = presentation.slides.add();
  bg(slide, ctx, C.ink);
  kicker(slide, ctx, "PLATFORM ARCHITECTURE", { textColor: "#B8C2CF" });
  title(slide, ctx, "A modular spatial cloud, already shaped for pilots and SDK integration.", { w: 920, size: 44, color: C.white });

  const lanes = [
    ["Client surfaces", "Next.js portal\nScene upload, dashboard, 3D viewer, localization sandbox\nUnity SDK\nVPSClient, MapSpace, coordinate conversion", 70, 190, 320, "#172331"],
    ["API and orchestration", "FastAPI\n/scene upload, process, frames, anchors, tiles\n/vps localize, evaluation, agent WebSocket\nCelery worker + Redis queue", 480, 190, 320, "#132732"],
    ["Spatial engine", "ffmpeg frame extraction\nCOLMAP Structure-from-Motion\nGaussian Splat / fallback PLY\nORB + SIFT fallback, FAISS, solvePnPRansac", 890, 190, 320, "#172331"],
  ];
  lanes.forEach(([label, detail, x, y, w, fill]) => {
    stage(slide, ctx, label, detail, x, y, w, 250, { fill, line: "#2F4658", color: C.lime, detailColor: "#C6CED8", labelSize: 20, detailSize: 15 });
  });

  rule(slide, ctx, 390, 316, 90, C.lime, 2);
  ctx.addText(slide, { text: "API calls", x: 408, y: 292, w: 86, h: 18, fontSize: 11, bold: true, color: C.lime, typeface: ctx.fonts.mono, insets: { left: 0, right: 0, top: 0, bottom: 0 } });
  rule(slide, ctx, 800, 316, 90, C.cyan, 2);
  ctx.addText(slide, { text: "jobs + data", x: 806, y: 274, w: 100, h: 18, fontSize: 11, bold: true, color: C.cyan, typeface: ctx.fonts.mono, insets: { left: 0, right: 0, top: 0, bottom: 0 } });

  stage(slide, ctx, "Storage layer", "PostgreSQL metadata | raw frames | recon outputs | splats | features | anchors", 180, 510, 920, 74, { fill: "#0E151D", line: "#2F4658", color: C.cyan, detailColor: "#C6CED8", labelSize: 17, detailSize: 14 });
  footer(slide, ctx, "Sources: backend/api/routes_scene.py; backend/api/routes_vps.py; backend/workers/tasks.py; unity-sdk/com.vps.sdk", true);
  return slide;
}
