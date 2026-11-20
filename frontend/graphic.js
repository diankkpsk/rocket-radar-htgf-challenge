// Schematic Germany outline, plotted as a halftone. This decorative map never
// represents company locations, measured signals or scan activity.
const boundary = [
  [8.6, 54.9],
  [9.4, 54.8],
  [9.8, 54.9],
  [10, 54.7],
  [10, 54.5],
  [10.3, 54.45],
  [10.1, 54.3],
  [10.8, 54.3],
  [11, 54.5],
  [11.25, 54.37],
  [10.77, 54.05],
  [11, 53.94],
  [11.3, 54.02],
  [11.45, 53.92],
  [12.1, 54.18],
  [12.35, 54.27],
  [12.5, 54.48],
  [12.95, 54.44],
  [13.12, 54.3],
  [13.37, 54.35],
  [13.22, 54.53],
  [13.45, 54.68],
  [13.68, 54.57],
  [13.67, 54.33],
  [13.42, 54.2],
  [13.76, 54.15],
  [13.88, 53.99],
  [14.26, 53.93],
  [14.37, 53.75],
  [14.23, 53.52],
  [14.43, 53.3],
  [14.37, 53.15],
  [14.13, 52.98],
  [14.14, 52.85],
  [14.58, 52.61],
  [14.65, 52.39],
  [14.55, 52.29],
  [14.71, 52.11],
  [14.7, 51.88],
  [14.62, 51.8],
  [14.9, 51.61],
  [14.96, 51.41],
  [15.02, 51.25],
  [14.81, 51.04],
  [14.83, 50.87],
  [14.57, 50.92],
  [14.38, 50.87],
  [14.31, 51.04],
  [14.05, 50.9],
  [13.82, 50.73],
  [13.53, 50.71],
  [13.12, 50.5],
  [12.8, 50.45],
  [12.52, 50.39],
  [12.36, 50.22],
  [12.16, 50.24],
  [12.13, 50.01],
  [12.45, 49.85],
  [12.39, 49.74],
  [12.59, 49.56],
  [12.69, 49.4],
  [12.93, 49.34],
  [13.18, 49.14],
  [13.43, 48.98],
  [13.68, 48.88],
  [13.82, 48.77],
  [13.69, 48.56],
  [13.48, 48.56],
  [13.43, 48.4],
  [13.13, 48.3],
  [12.89, 48.2],
  [12.74, 48.13],
  [12.97, 47.86],
  [12.89, 47.73],
  [13.09, 47.64],
  [12.99, 47.48],
  [12.83, 47.5],
  [12.76, 47.67],
  [12.51, 47.65],
  [12.22, 47.71],
  [12.24, 47.62],
  [11.89, 47.61],
  [11.62, 47.58],
  [11.42, 47.5],
  [11.23, 47.42],
  [11.07, 47.39],
  [10.92, 47.48],
  [10.59, 47.54],
  [10.47, 47.42],
  [10.22, 47.28],
  [10.12, 47.41],
  [10.02, 47.48],
  [9.99, 47.55],
  [9.69, 47.54],
  [9.54, 47.54],
  [9.24, 47.66],
  [8.89, 47.66],
  [8.57, 47.77],
  [8.42, 47.62],
  [8.2, 47.62],
  [7.94, 47.55],
  [7.69, 47.57],
  [7.54, 47.53],
  [7.62, 47.68],
  [7.53, 47.81],
  [7.58, 48.06],
  [7.74, 48.32],
  [7.81, 48.57],
  [8.08, 48.91],
  [8.23, 48.97],
  [8.04, 49.06],
  [7.65, 49.05],
  [7.38, 49.19],
  [7.09, 49.12],
  [6.81, 49.17],
  [6.72, 49.34],
  [6.54, 49.42],
  [6.37, 49.48],
  [6.47, 49.81],
  [6.23, 49.88],
  [6.11, 50.04],
  [6.19, 50.22],
  [6.37, 50.33],
  [6.19, 50.5],
  [6.03, 50.78],
  [5.88, 50.8],
  [6.08, 51.02],
  [5.96, 51.04],
  [6.21, 51.24],
  [6.18, 51.38],
  [6.09, 51.49],
  [6.05, 51.67],
  [5.96, 51.76],
  [6.17, 51.89],
  [6.39, 51.84],
  [6.7, 51.93],
  [6.81, 51.99],
  [6.69, 52.06],
  [7.05, 52.4],
  [6.73, 52.46],
  [6.71, 52.61],
  [7.04, 52.64],
  [7.1, 52.85],
  [7.22, 53.04],
  [7.2, 53.2],
  [7.03, 53.31],
  [7.02, 53.49],
  [7.2, 53.67],
  [7.58, 53.69],
  [7.87, 53.73],
  [8.06, 53.64],
  [8.13, 53.48],
  [8.3, 53.52],
  [8.36, 53.63],
  [8.5, 53.57],
  [8.49, 53.72],
  [8.67, 53.89],
  [8.9, 53.91],
  [9.05, 53.88],
  [8.91, 54.07],
  [8.83, 54.22],
  [8.61, 54.3],
  [8.63, 54.38],
  [8.86, 54.4],
  [8.93, 54.55],
  [8.68, 54.62],
  [8.61, 54.75],
];
export function paintMap(canvas) {
  if (!canvas) return;
  const { width: w, height: h } = canvas.getBoundingClientRect();
  if (!w || !h) return;
  const scale = Math.min(window.devicePixelRatio || 1, 2);
  canvas.width = w * scale;
  canvas.height = h * scale;
  const ctx = canvas.getContext("2d");
  if (!ctx) return;
  ctx.scale(scale, scale);
  const cx = w * 0.53,
    cy = h * 0.53,
    sp = h / 9;
  const project = ([x, y]) => [
    cx + (x - 10.5) * sp * 0.83,
    cy - (y - 51.2) * sp,
  ];
  const path = new Path2D();
  boundary.forEach((p, i) => path[i ? "lineTo" : "moveTo"](...project(p)));
  path.closePath();
  const line = (a, b, c, d, color, size = 1) => {
    ctx.strokeStyle = color;
    ctx.lineWidth = size;
    ctx.beginPath();
    ctx.moveTo(a, b);
    ctx.lineTo(c, d);
    ctx.stroke();
  };
  ctx.save();
  ctx.clip(path);
  ctx.fillStyle = "#cadccc";
  ctx.fillRect(0, 0, w, h);
  for (let y = 0; y < h; y += 3.8)
    for (let x = (Math.round(y / 3.8) % 2) * 1.9; x < w; x += 3.8) {
      ctx.fillStyle = "#789c87";
      ctx.fillRect(x, y, 1.15, 1.15);
    }
  ctx.restore();
  ctx.strokeStyle = "#94af9c";
  ctx.lineWidth = 0.8;
  ctx.stroke(path);
  const [px, py] = project([10.15, 51.15]);
  const radius = h * 0.58;
  const sweep = ctx.createLinearGradient(px, py, px + radius, py - radius);
  sweep.addColorStop(0, "rgba(55,130,97,.03)");
  sweep.addColorStop(1, "rgba(55,130,97,.14)");
  ctx.fillStyle = sweep;
  ctx.beginPath();
  ctx.moveTo(px, py);
  ctx.arc(px, py, radius, -1.24, -0.65);
  ctx.closePath();
  ctx.fill();
  [0.28, 0.57, 0.86, 1.15].forEach((r, i) => {
    ctx.beginPath();
    ctx.strokeStyle = i % 2 ? "#adbfac" : "#bcccb8";
    ctx.lineWidth = 0.65;
    ctx.arc(px, py, radius * r, 0, Math.PI * 2);
    ctx.stroke();
  });
  line(
    px,
    py,
    px + radius * Math.cos(-0.65),
    py + radius * Math.sin(-0.65),
    "#9fbba5",
    0.95,
  );
  line(px - radius * 1.24, py, px + radius * 1.24, py, "#b5c7b7", 0.55);
  line(px, py - radius * 1.05, px, py + radius * 1.05, "#b5c7b7", 0.55);
  [
    ["Berlin", [13.4, 52.52], 1],
    ["Munich", [11.58, 48.14], 1],
    ["Bonn", [7.1, 50.74], -1],
  ].forEach(([name, coords, dir]) => {
    const [x, y] = project(coords);
    line(x, y, x + dir * 8, y - 8, "#6c8d77", 0.75);
    line(x + dir * 8, y - 8, x + dir * 15, y - 8, "#6c8d77", 0.75);
    ctx.fillStyle = "#2e5e4d";
    ctx.beginPath();
    ctx.arc(x, y, 2.3, 0, Math.PI * 2);
    ctx.fill();
    ctx.font = "9px ui-monospace, Menlo, monospace";
    ctx.textAlign = dir > 0 ? "left" : "right";
    ctx.fillText(name.toUpperCase(), x + dir * 18, y - 5.4);
  });
}
