export const C = {
  paper: "#F7F4ED",
  ink: "#101820",
  ink2: "#172331",
  lime: "#B7F64B",
  cyan: "#37C8D6",
  rust: "#E56B45",
  muted: "#667085",
  line: "#D8D3C7",
  white: "#FFFFFF",
  pale: "#ECE7DA",
};

export function bg(slide, ctx, color = C.paper) {
  ctx.addShape(slide, { x: 0, y: 0, w: ctx.W, h: ctx.H, fill: color });
}

export function title(slide, ctx, text, opts = {}) {
  return ctx.addText(slide, {
    text,
    x: opts.x ?? 72,
    y: opts.y ?? 64,
    w: opts.w ?? 760,
    h: opts.h ?? 110,
    fontSize: opts.size ?? 48,
    bold: true,
    typeface: ctx.fonts.title,
    color: opts.color ?? C.ink,
    insets: { left: 0, right: 0, top: 0, bottom: 0 },
  });
}

export function kicker(slide, ctx, text, opts = {}) {
  const x = opts.x ?? 72;
  const y = opts.y ?? 36;
  ctx.addShape(slide, { x, y: y + 6, w: 28, h: 4, fill: opts.color ?? C.lime });
  return ctx.addText(slide, {
    text,
    x: x + 42,
    y,
    w: opts.w ?? 360,
    h: 18,
    fontSize: 11,
    bold: true,
    color: opts.textColor ?? C.muted,
    typeface: ctx.fonts.mono,
    insets: { left: 0, right: 0, top: 0, bottom: 0 },
  });
}

export function body(slide, ctx, text, opts = {}) {
  return ctx.addText(slide, {
    text,
    x: opts.x ?? 72,
    y: opts.y ?? 174,
    w: opts.w ?? 520,
    h: opts.h ?? 100,
    fontSize: opts.size ?? 21,
    color: opts.color ?? C.muted,
    typeface: ctx.fonts.body,
    insets: { left: 0, right: 0, top: 0, bottom: 0 },
  });
}

export function footer(slide, ctx, text, dark = false) {
  return ctx.addText(slide, {
    text,
    x: 72,
    y: 684,
    w: 900,
    h: 18,
    fontSize: 9,
    color: dark ? "#9AA4B2" : "#8A8174",
    typeface: ctx.fonts.mono,
    insets: { left: 0, right: 0, top: 0, bottom: 0 },
  });
}

export function chip(slide, ctx, text, x, y, w, opts = {}) {
  ctx.addShape(slide, {
    x,
    y,
    w,
    h: opts.h ?? 36,
    fill: opts.fill ?? C.white,
    line: ctx.line(opts.line ?? C.line, 1),
  });
  return ctx.addText(slide, {
    text,
    x: x + 14,
    y: y + 8,
    w: w - 28,
    h: 18,
    fontSize: opts.size ?? 13,
    bold: true,
    color: opts.color ?? C.ink,
    typeface: ctx.fonts.body,
    insets: { left: 0, right: 0, top: 0, bottom: 0 },
  });
}

export function metric(slide, ctx, value, label, x, y, w, opts = {}) {
  ctx.addShape(slide, { x, y, w, h: 94, fill: opts.fill ?? C.white, line: ctx.line(opts.line ?? C.line, 1) });
  ctx.addText(slide, { text: value, x: x + 18, y: y + 16, w: w - 36, h: 34, fontSize: 28, bold: true, color: opts.valueColor ?? C.ink, typeface: ctx.fonts.title, insets: { left: 0, right: 0, top: 0, bottom: 0 } });
  ctx.addText(slide, { text: label, x: x + 18, y: y + 54, w: w - 36, h: 28, fontSize: 11, bold: true, color: opts.labelColor ?? C.muted, typeface: ctx.fonts.mono, insets: { left: 0, right: 0, top: 0, bottom: 0 } });
}

export function stage(slide, ctx, label, detail, x, y, w, h, opts = {}) {
  ctx.addShape(slide, { x, y, w, h, fill: opts.fill ?? C.white, line: ctx.line(opts.line ?? C.line, 1) });
  const labelY = opts.labelY ?? 16;
  const detailY = opts.detailY ?? 48;
  const detailH = opts.detailH ?? Math.max(h - detailY - 14, 20);
  ctx.addText(slide, { text: label, x: x + 18, y: y + labelY, w: w - 36, h: opts.labelH ?? 28, fontSize: opts.labelSize ?? 18, bold: true, color: opts.color ?? C.ink, typeface: ctx.fonts.title, insets: { left: 0, right: 0, top: 0, bottom: 0 } });
  ctx.addText(slide, { text: detail, x: x + 18, y: y + detailY, w: w - 36, h: detailH, fontSize: opts.detailSize ?? 13, color: opts.detailColor ?? C.muted, typeface: ctx.fonts.body, insets: { left: 0, right: 0, top: 0, bottom: 0 } });
}

export function rule(slide, ctx, x, y, w, color = C.line, h = 1) {
  ctx.addShape(slide, { x, y, w, h, fill: color });
}
