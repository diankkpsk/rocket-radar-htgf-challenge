const glyphs = {
  search: '<circle cx="10.8" cy="10.8" r="6.6"/><path d="m16 16 4.4 4.4"/>',
  radar:
    '<path d="M20.6 8.2a9 9 0 1 1-4.8-4.7M16.7 10a5 5 0 1 1-2.9-2.8M12 12l8-8"/><circle cx="12" cy="12" r=".8"/>',
  target:
    '<circle cx="12" cy="12" r="8.5"/><circle cx="12" cy="12" r="4.7"/><circle cx="12" cy="12" r="1"/>',
  structure:
    '<rect x="3" y="13.3" width="6.3" height="6.3" rx="1.1"/><rect x="14.5" y="13.3" width="6.3" height="6.3" rx="1.1"/><rect x="8.7" y="2.7" width="6.3" height="6.3" rx="1.1"/><path d="M12 9v2.1M6.1 13.3v-2.2h11.6v2.2"/>',
  layers: '<path d="m12 3 9 5-9 5-9-5zM3 12l9 5 9-5M3 16l9 5 9-5"/>',
  bookmark:
    '<path d="M6 4.5c0-.8.7-1.5 1.5-1.5h9c.8 0 1.5.7 1.5 1.5V21l-6-4-6 4z"/>',
  gear: '<path d="m11 2.8 2 .1.8 2.1 2 .8 2.1-.9 1.4 1.4-.9 2.1.8 2 2.1.8v2l-2.1.8-.8 2 .9 2.1-1.4 1.4-2.1-.9-2 .8-.8 2.1h-2l-.8-2.1-2-.8-2.1.9L4.7 18l.9-2.1-.8-2-2.1-.8v-2l2.1-.8.8-2-.9-2.1 1.4-1.4 2.1.9 2-.8z"/><circle cx="12" cy="12" r="3.1"/>',
  filter:
    '<path d="M3 6h8m5 0h5M3 12h2m5 0h11M3 18h10m5 0h3"/><circle cx="13.5" cy="6" r="2.1"/><circle cx="7.5" cy="12" r="2.1"/><circle cx="15.5" cy="18" r="2.1"/>',
  arrow: '<path d="M4 12h15m-6-6 6 6-6 6"/>',
  upRight: '<path d="M6 18 18 6M7 6h11v11"/>',
  down: '<path d="m6 9 6 6 6-6"/>',
  export: '<path d="M12 3v12m-4-4 4 4 4-4M4 16v4h16v-4"/>',
  plus: '<path d="M12 5v14m-7-7h14"/>',
  check: '<path d="m4 12 5 5L20 6"/>',
  pin: '<path d="M19.2 9.6c0 4.7-7.2 11.3-7.2 11.3S4.8 14.3 4.8 9.6a7.2 7.2 0 1 1 14.4 0Z"/><circle cx="12" cy="9.5" r="2.2"/>',
  book: '<path d="M4 4.8c3.7-1.1 6.2-.5 8 1.3 2-1.8 4.9-2.3 8-1.3v13.6c-3.1-.9-6-.5-8 1.3-1.8-1.8-4.4-2.2-8-1.3zM12 6v14"/>',
  signal: '<path d="M2 12h5l2.5-6 4.3 12 2.6-6H22"/>',
  clock: '<circle cx="12" cy="12" r="8.8"/><path d="M12 7v5.2l3.5 2.1"/>',
  diamond:
    '<path d="m12 2 2.5 6.8 6.5 3.1-6.5 2.7L12 22l-2.8-7.4L3 12l6.2-3.2z"/>',
  arrowLeft: '<path d="m14.5 5-7 7 7 7"/>',
  arrowRight: '<path d="m9 5 7 7-7 7"/>',
  close: '<path d="m5 5 14 14M19 5 5 19"/>',
  portfolio:
    '<rect x="3" y="7" width="18" height="13.5" rx="2"/><path d="M8 7V4.5h8V7M3 12.5a25 25 0 0 0 18 0"/>',
  globe:
    '<circle cx="12" cy="12" r="9"/><ellipse cx="12" cy="12" rx="4.4" ry="9"/><path d="M3 12h18"/>',
  user: '<circle cx="12" cy="7.6" r="3.8"/><path d="M4.7 20c.6-5.8 4-7.1 7.3-7.1s6.7 1.3 7.3 7.1"/>',
  refresh:
    '<path d="M20 9a8.4 8.4 0 0 0-14-3l-2 2M4 3v5h5M4 15a8.4 8.4 0 0 0 14 3l2-2m0 5v-5h-5"/>',
  file: '<path d="M5 3h9l5 5v13H5zM14 3v5h5M8 13h8M8 17h5"/>',
  bars: '<path d="M3 19h18M6 15v-4M12 15V5m6 10V8"/>',
  activity: '<path d="M3 19V5M3 19h18M5.5 14.5l4-5 4 3.5 6-7"/>',
  menu: '<path d="M3 6h18M3 12h18M3 18h18"/>',
};
export function icon(key) {
  return (
    '<svg class="ico" viewBox="0 0 24 24" aria-hidden="true" focusable="false">' +
    (glyphs[key] || "") +
    "</svg>"
  );
}
export const e = (s) =>
  String(s ?? "").replace(
    /[&<>"']/g,
    (c) =>
      ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[
        c
      ],
  );
export function href(raw) {
  try {
    const u = new URL(raw);
    return ["http:", "https:"].includes(u.protocol) &&
      !u.username &&
      !u.password
      ? e(u.href)
      : "";
  } catch {
    return "";
  }
}
export function link(raw, label) {
  const url = href(raw);
  return url
    ? '<a class="evidence-link" href="' +
        url +
        '" rel="noopener noreferrer" target="_blank">' +
        e(label) +
        " " +
        icon("upRight") +
        "</a>"
    : e(label);
}
export const label = (s) =>
  String(s ?? "")
    .toLowerCase()
    .replaceAll("_", " ")
    .replace(/\b\p{L}/u, (x) => x.toUpperCase());
const stageNames = {
  POTENTIAL_PRE_COMPANY: "Pre-company",
  NEWLY_INCORPORATED: "Newly registered",
  EXISTING_EMERGING: "Emerging",
  RESEARCH_ONLY: "Research only",
  NOT_A_STARTUP: "Excluded",
  UNKNOWN: "Stage unknown",
};
export const stageLabel = (s, kind) =>
  kind === "portfolio"
    ? "HTGF portfolio"
    : stageNames[s] || label(s) || "Stage unknown";
export const stageTone = (s, kind) =>
  kind === "portfolio"
    ? "slate"
    : s === "POTENTIAL_PRE_COMPANY"
      ? "emerald"
      : s === "NEWLY_INCORPORATED"
        ? "blue"
        : s === "EXISTING_EMERGING"
          ? "amber"
          : "slate";
export const pill = (txt, tone = "slate") =>
  '<span class="pill ' + e(tone) + '">' + e(txt) + "</span>";
const regions = new Intl.DisplayNames(["en"], { type: "region" });
export function country(x) {
  if (!x) return "";
  try {
    return /^[A-Z]{2}$/.test(x) ? regions.of(x) : x;
  } catch {
    return x;
  }
}
export function date(x, withTime = false) {
  if (!x) return "Unknown";
  if (/^\d{4}(-\d{2})?$/.test(x)) return x;
  const d = new Date(x);
  if (isNaN(d.getTime())) return String(x);
  return new Intl.DateTimeFormat("en-GB", {
    timeZone: "UTC",
    day: "2-digit",
    month: "short",
    year: "numeric",
    ...(withTime && String(x).includes("T")
      ? { hour: "2-digit", minute: "2-digit", timeZoneName: "short" }
      : {}),
  }).format(d);
}
export function mono(name = "") {
  const words = name.trim().split(/\s+/),
    initials =
      words.length > 1
        ? words[0][0] + words[1][0]
        : [...name].slice(0, 2).join("");
  let h = 0;
  for (const c of name) h = (h * 31 + c.codePointAt(0)) >>> 0;
  return (
    '<span aria-hidden="true" class="monogram tint' +
    (h % 6) +
    '">' +
    e(initials.toLocaleUpperCase()) +
    "</span>"
  );
}
export function score(value) {
  return Number.isFinite(value) ? String(Math.round(value)) : "—";
}
export const keyText = (v, empty = "Unknown") => (v ? label(v) : empty);
export const statusTone = (s) =>
  /fail|error|restrict|block/i.test(s)
    ? "red"
    : /requi|manual|partial|key|planned|lookup|document/i.test(s)
      ? "amber"
      : /live|enable|success|complet|replay|record|working/i.test(s)
        ? "emerald"
        : "slate";
export function empty(title, body, ico = "search", action = "") {
  return (
    '<div class="empty"><span class="empty-ico">' +
    icon(ico) +
    "</span><h3>" +
    e(title) +
    "</h3><p>" +
    e(body) +
    "</p>" +
    action +
    "</div>"
  );
}
