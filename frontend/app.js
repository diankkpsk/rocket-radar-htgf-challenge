import { paintMap } from "./graphic.js";
import {
  icon,
  e,
  href,
  link,
  label,
  stageLabel,
  stageTone,
  pill,
  country,
  date,
  mono,
  score,
  keyText,
  statusTone,
  empty,
} from "./ui.js";

const BASE = "/api/v1";
const $ = (s) => document.querySelector(s);
const main = $("#main"),
  detailDialog = $("#detail-dialog"),
  actionDialog = $("#action-dialog");
const navViews = [
  ["discover", "Discovery", "radar"],
  ["portfolio", "HTGF portfolio", "portfolio"],
  ["watchlist", "Watchlist", "bookmark"],
  ["sources", "Sources", "layers"],
  ["activity", "Scan history", "activity"],
];
const stages = [
  ["", "All leads"],
  ["POTENTIAL_PRE_COMPANY", "Pre-company"],
  ["NEWLY_INCORPORATED", "New registrations"],
  ["EXISTING_EMERGING", "Emerging"],
];
const params = () => new URLSearchParams(location.search);
const pageView = () => params().get("view") || "discover";
const relevant = ["discover", "portfolio", "watchlist"];
const moreFilters = [
  "country",
  "sector",
  "source",
  "min_quality",
  "min_confidence",
  "days",
  "scope",
  "university",
  "funding_status",
  "registration_status",
  "review_status",
  "observed_from",
  "observed_to",
  "published_from",
  "published_to",
  "watch",
];
const fields = ["q", "stage", "sort", "page", ...moreFilters];
let stats = {},
  sources = [],
  coverage = [],
  sourceError = "",
  coverageError = "",
  scanRows = [],
  changeRows = [],
  opsQuery = "",
  opsTab = "sources",
  filtersOpen = false,
  searchTimer = 0,
  renderEpoch = 0,
  listEpoch = 0,
  toastTimer = 0,
  scanTimer = 0,
  activeDetail = null;
let preferences = {};
let planner = {country:"", technology:"", items:[], configured:false, query:"", response:null, ready:false, feedback:""};
let listing = { items: [], total: 0, facets: {} };
let filterExtrasOpen = false,
  inbox = [],
  pairs = [];
async function api(path, body) {
  const options =
    body === undefined
      ? {}
      : {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        };
  const res = await fetch(BASE + path, { ...options, cache: "no-store" });
  let data = null;
  try {
    data = await res.json();
  } catch {}
  if (!res.ok) {
    const details = Array.isArray(data?.detail)
      ? data.detail.map((x) => x.msg).join(". ")
      : data?.detail;
    const message =
      data?.detail?.message ||
      details ||
      data?.error?.message ||
      data?.error ||
      `Request failed (${res.status})`;
    throw Error(
      typeof message === "string"
        ? message
        : "The server could not process this request.",
    );
  }
  return data;
}
const items = (d) => (Array.isArray(d) ? d : d?.items || []);
function setParams(changes, replace = false) {
  const u = new URL(location.href);
  for (const [key, value] of Object.entries(changes)) {
    if (value == null || value === "") u.searchParams.delete(key);
    else u.searchParams.set(key, value);
  }
  if (!u.searchParams.size) u.searchParams.set("view", "discover");
  history[replace ? "replaceState" : "pushState"](null, "", u);
}
const asListParams = () => {
  const p = params(),
    a = new URLSearchParams();
  for (const k of fields) if (p.get(k) && k !== "scope") a.set(k, p.get(k));
  const view = pageView();
  a.set(
    "kind",
    view === "portfolio"
      ? "portfolio"
      : view === "watchlist" || p.get("scope") === "all"
        ? "all"
        : "prospect",
  );
  if (view === "watchlist") a.set("watch", "true");
  a.set("limit", "12");
  return a;
};
const filterCount = () => moreFilters.filter((k) => params().get(k)).length;
const routeLink = (view, extra = {}) => {
  const p = new URLSearchParams({ view, ...extra });
  return "?" + e(p.toString());
};
function nav() {
  const view = pageView();
  $("#nav").innerHTML = navViews
    .map(
      ([id, name, ic]) =>
        `<a class="navlink" data-view="${id}" href="${routeLink(id)}" ${view === id ? 'aria-current="page"' : ""}>${icon(ic)}${e(name)}${id === "watchlist" && stats.watchlist > 0 ? `<span class="nav-count">${e(stats.watchlist)}</span>` : ""}</a>`,
    )
    .join("");
  $(".gear").innerHTML = icon("gear");
  $(".scan-btn").innerHTML = `${icon("radar")}Run scan`;
}
function goto(view, extra = {}) {
  clearTimeout(searchTimer);
  if (detailDialog.open) detailDialog.close();
  if (actionDialog.open) actionDialog.close();
  const u = new URL(location.href);
  u.search = new URLSearchParams({ view, ...extra }).toString();
  u.hash = "";
  history.pushState(null, "", u);
  filtersOpen = moreFilters.some((k) => params().has(k));
  opsQuery = "";
  opsTab = "sources";
  window.scrollTo({ top: 0 });
  render();
}
function notify(message) {
  const t = $("#toast");
  t.textContent = message;
  t.classList.add("visible");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.remove("visible"), 3600);
}
function metrics() {
  const entries = [
    ["radar", "Discovery leads", stats.prospects, ""],
    ["portfolio", "HTGF portfolio", stats.portfolio, "blue"],
    ["layers", "Evidence items", stats.evidence, "ochre"],
    ["bookmark", "On watchlist", stats.watchlist, "lilac"],
  ];
  return `<div class="metrics" aria-label="Workspace totals">${entries.map(([ic, name, n, cl]) => `<div class="metric"><span class="metric-icon ${cl}">${icon(ic)}</span><div><strong class="metric-num">${e(n ?? "—")}</strong><span class="metric-label">${name}</span></div></div>`).join("")}</div>`;
}
function hero() {
  const view = pageView();
  const titles = {
    discover: [
      "Venture discovery",
      "Find European venture teams through the public signals they leave behind.",
    ],
    portfolio: [
      "HTGF portfolio",
      "Search recorded portfolio companies and open their original HTGF profiles.",
    ],
    watchlist: [
      "Your watchlist",
      "Revisit saved ventures, review their evidence, and update your research notes.",
    ],
  };
  const [title, desc] = titles[view];
  return `<div class="top-hero"><div class="wrap hero-shell"><div class="hero-copy"><div class="context">HTGF research workspace</div><h1>${title}</h1><p>${desc}</p></div><div class="map-art" aria-hidden="true"><canvas id="radar-map"></canvas></div></div></div>`;
}
function sourceStatus(s) {
  return keyText(s.status || s.mode, "Unknown");
}
function rail() {
  const best = stats.best_find;
  const featured = best
    ? `<article class="best-card"><div class="eyebrow">${icon("target")} Best find</div><h2>${e(best.name)}</h2><p>${e(best.best_find?.rationale || best.why_now || best.summary)}</p><a class="best-link" href="${routeLink("best")}" data-view="best">Open research brief ${icon("arrow")}</a></article>`
    : "";
  const shown = sources
    .filter((s) => s.can_scan || s.last_success_at)
    .slice(0, 3);
  const coverageBlock = `<section class="rail-card card"><div class="rail-head"><h2>Source coverage</h2>${icon("layers")}</div>${shown.length ? shown.map((s) => `<div class="rail-row"><div><strong>${e(s.name)}</strong><small>${e(keyText(s.kind, "Source"))}</small></div>${pill(sourceStatus(s), statusTone(s.status || s.mode))}</div>`).join("") : `<p class="hint">${e(sourceError || "No active sources in the directory.")}</p>`}<a class="foot-link" href="${routeLink("sources")}" data-view="sources">View all sources ${icon("arrow")}</a></section>`;
  return `${featured}${coverageBlock}<div class="source-stamp">${icon("clock")}<div>${e({ recorded: "Recorded public evidence", mixed: "Live and recorded evidence", live: "Live-collected evidence" }[stats.mode] || "Local evidence index")}${stats.as_of ? `<br>As of ${e(date(stats.as_of))}` : ""}</div></div>`;
}
function filters() {
  const p = params(),
    facets = listing.facets || {};
  const option = (v, n, sel) =>
    `<option value="${e(v)}" ${String(v) === String(sel ?? "") ? "selected" : ""}>${e(n)}</option>`;
  const make = (key, caption, opts, emptyLabel = "Any") =>
    `<label>${e(caption)}<select data-filter="${key}">${option("", emptyLabel, p.get(key))}${opts.map(([v, n]) => option(v, n, p.get(key))).join("")}</select></label>`;
  const countries = (facets.countries || []).map((x) => [
      x.value || x.code || x,
      country(x.value || x.code || x),
    ]),
    sectors = (facets.sectors || []).map((x) => [
      x.value || x,
      x.label || x.value || x,
    ]);
  const field = (key, title, type = "text") =>
    `<label>${e(title)}<input data-filter="${key}" type="${type}" value="${e(p.get(key))}"></label>`;
  const sourceOpts = (facets.sources || []).map((x) => {
    const id = x.id || x.value || x;
    return [id, x.name || sources.find((s) => s.id === id)?.name || id];
  });
  return `<div class="filters">${make("country", "Country", countries)}${make("sector", "Sector", sectors)}${make("source", "Source", sourceOpts)}${make(
    "min_quality",
    "Minimum quality",
    [25, 50, 75].map((x) => [x, `${x} / 100`]),
  )}${make(
    "min_confidence",
    "Minimum confidence",
    [25, 50, 75].map((x) => [x, `${x} / 100`]),
  )}${pageView() === "discover" ? make("scope", "Search scope", [["all", "Discovery + HTGF portfolio"]], "Discovery leads") : ""}${
    p.get("stage") === "NEWLY_INCORPORATED"
      ? make(
          "days",
          "Registration window",
          [
            [7, "Last 7 days"],
            [30, "Last 30 days"],
          ],
          "Last 90 days",
        )
      : ""
  }<div class="filter-extra"><details id="filter-extra" ${filterExtrasOpen ? "open" : ""}><summary>Verification &amp; dates</summary><div class="extra-grid">${field("university", "University or programme")}${make(
    "funding_status",
    "Funding verification",
    [
      ["VERIFIED_FUNDING_ANNOUNCED", "Announced"],
      ["NO_VERIFIED_FUNDING_FOUND", "No verified funding found"],
      ["UNKNOWN", "Unknown"],
      ["CONFLICTING", "Conflicting"],
    ],
  )}${make("registration_status", "Registration verification", [
    ["VERIFIED_REGISTERED", "Verified registration"],
    ["NOT_VERIFIED", "No verified registration found"],
    ["PENDING_REVIEW", "Pending review"],
    ["CONFLICTING", "Conflicting"],
  ])}${make("review_status", "Analyst decision", [
    ["unreviewed", "Unreviewed"],
    ["accept", "Accept"],
    ["reject", "Reject"],
    ["review", "Needs review"],
    ["watch", "Watch"],
  ])}${pageView() !== "watchlist" ? make("watch", "Watchlist", [["true", "Saved only"]]) : ""}${field("observed_from", "First observed from", "date")}${field("observed_to", "First observed through", "date")}${field("published_from", "Source published from", "date")}${field("published_to", "Source published through", "date")}</div></details></div><div class="filters-actions"><button class="text-btn" data-action="clear">Reset search &amp; filters</button></div></div>`;
}
function controls() {
  const p = params(),
    v = pageView(),
    stage = p.get("stage") || "",
    count = filterCount();
  $("#filter-btn").classList.toggle("active", filtersOpen || count > 0);
  $("#filter-btn").setAttribute("aria-expanded", String(filtersOpen));
  $("#filter-btn").innerHTML =
    `${icon("filter")}Filters${count ? ` (${count})` : ""}`;
  $("#filter-box").innerHTML = filtersOpen ? filters() : "";
  $("#feed-tabs").innerHTML =
    v === "discover"
      ? stages
          .map(
            ([key, title]) =>
              `<button type="button" class="feed-tab ${stage === key ? "active" : ""}" aria-pressed="${stage === key}" data-stage="${key}">${title}</button>`,
          )
          .join("")
      : "";
  $("#export-csv").href = BASE + "/exports/leads.csv?" + asListParams();
  $("#q").placeholder =
    v === "portfolio"
      ? "Search portfolio companies or technologies…"
      : v === "watchlist"
        ? "Search saved ventures or evidence…"
        : "Search ventures, technologies, or signals…";
}
function researchShell() {
  const v = pageView(),
    title = {
      discover: "Discovery feed",
      portfolio: "Portfolio directory",
      watchlist: "Saved ventures",
    }[v];
  main.innerHTML = `${hero()}<div class="wrap page-body"><div id="metrics">${metrics()}</div><div class="research-grid"><section class="list-panel" aria-label="Venture results"><div class="panel-top"><h2>${title}<span id="list-count"></span></h2><a class="text-btn" id="export-csv" download>${icon("export")}Export CSV</a></div><div class="search-row"><div class="search-field">${icon("search")}<input id="q" type="search" autocomplete="off" spellcheck="false" aria-label="Search ventures and evidence" value="${e(params().get("q"))}"><kbd aria-hidden="true">/</kbd></div><button type="button" id="filter-btn" class="filter-btn" data-action="filters" aria-controls="filter-box"></button></div><div id="filter-box"></div><div id="feed-tabs" class="feed-tabs"></div><div id="result-region" aria-live="polite"><div class="loading-panel" role="status">Searching the local index…</div></div></section><aside class="side-rail" id="side-rail">${rail()}</aside></div></div>`;
  if (v !== "discover") $("#feed-tabs").style.height = "12px";
  controls();
  paintMap($("#radar-map"));
}
function normalizeSignal(t) {
  const signals = {
    EXIST_GRANT: "EXIST grant",
    GITHUB_RELEASE: "GitHub release",
    AI_DEMO: "AI demo",
    STARTUP_PROGRAMME: "Startup programme",
    PILOT_CUSTOMERS: "Pilot customers",
    MARKET_LAUNCH: "Market launch",
    COMMERCIAL_RESEARCH: "Commercial research",
    ACCELERATOR_ACCEPTANCE: "Accelerator acceptance",
    PORTFOLIO_LISTING: "Portfolio listing",
  };
  return signals[t] || keyText(t, "");
}
function strongest(l) {
  const es = l.evidence || [];
  const cited = new Set(
    (l.scores?.breakdown || [])
      .filter((v) => v.score > 0)
      .flatMap((v) => v.evidence_ids || []),
  );
  const ev =
    es.find((x) => cited.has(x.id) && x.claim === l.why_now) ||
    es.find((x) => cited.has(x.id) && x.signal_type !== "OTHER") ||
    es.find((x) => x.signal_type && x.signal_type !== "OTHER") ||
    es[0];
  return ev
    ? {
        title:
          normalizeSignal(ev.signal_type) ||
          ev.source_name ||
          "Source evidence",
        url: ev.url,
      }
    : null;
}
function resultRow(l) {
  const sig = strongest(l),
    loc = [l.city, country(l.country)].filter(Boolean).join(", "),
    stage = stageLabel(l.stage, l.kind);
  const sourceCount = l.independent_sources ?? l.evidence_count;
  return `<li class="result"><div class="result-body">${mono(l.name)}<div><div class="result-name"><a href="${routeLink(pageView(), { lead: l.id })}" data-lead="${e(l.id)}">${e(l.name)}</a>${pill(stage, stageTone(l.stage, l.kind))}</div><p class="result-summary">${e(l.summary || l.why_now || "Open the dossier to review the recorded evidence.")}</p><div class="result-meta">${loc ? `<span>${icon("pin")}${e(loc)}</span>` : ""}${sig && href(sig.url) ? `<a class="result-signal" href="${href(sig.url)}" target="_blank" rel="noopener noreferrer" title="Open signal source">${icon("signal")}${e(sig.title)}</a>` : ""}${sourceCount != null ? `<span title="${l.independent_sources != null ? "Independent sources" : "Evidence items"}">${icon("layers")}${e(sourceCount)} ${l.independent_sources != null ? "source" : "item"}${sourceCount === 1 ? "" : "s"}</span>` : ""}${l.kind !== "portfolio" && Number.isFinite(l.scores?.quality) ? `<span title="Quality and confidence scores out of 100">${icon("bars")}Quality ${e(score(l.scores.quality))} · Confidence ${e(score(l.scores.confidence))}</span>` : ""}${l.first_observed_at ? `<span title="First observed by FounderRadar">${icon("clock")}Observed ${e(date(l.first_observed_at))}</span>` : ""}</div></div></div><button class="save-btn ${l.watched ? "is-saved" : ""}" type="button" aria-pressed="${Boolean(l.watched)}" aria-label="${l.watched ? "Remove from" : "Add to"} watchlist: ${e(l.name)}" title="${l.watched ? "Remove from" : "Add to"} watchlist" data-watch="${e(l.id)}" data-watched="${Boolean(l.watched)}">${icon("bookmark")}</button></li>`;
}
function resultView() {
  const p = params(),
    total = Number(listing.total) || 0,
    limit = Number(listing.limit) || 12,
    page = Number(listing.page) || 1,
    sort = p.get("sort") || "priority";
  const pos = Math.min((page - 1) * limit + 1, total),
    end = Math.min(page * limit, total),
    pages = Math.ceil(total / limit);
  const options = [
    ["priority", "Investor priority"],
    ["quality", "Quality"],
    ["confidence", "Confidence"],
    ["recent", "Most recent signal"],
    ["name", "Name A–Z"],
  ]
    .map(
      ([id, n]) =>
        `<option value="${id}" ${sort === id ? "selected" : ""}>${n}</option>`,
    )
    .join("");
  const isFiltered = fields.some(
    (k) => !["page", "sort"].includes(k) && p.has(k),
  );
  const emptyTitle =
    p.get("stage") === "NEWLY_INCORPORATED"
      ? "No verified registrations in this window"
      : isFiltered
        ? "No matching ventures"
        : pageView() === "watchlist"
          ? "Your watchlist is empty"
          : "No verified leads found yet";
  const msg = isFiltered
    ? "Try broadening your search, stage or filters."
    : pageView() === "watchlist"
      ? "Use the bookmark beside a venture to save it here."
      : "Run a scan or open Sources to inspect coverage.";
  const clear = isFiltered
    ? '<button class="secondary" data-action="clear">Clear filters</button>'
    : `<a class="secondary" data-view="${pageView() === "watchlist" ? "discover" : "sources"}" href="${routeLink(pageView() === "watchlist" ? "discover" : "sources")}">${pageView() === "watchlist" ? "Explore ventures" : "Inspect sources"}</a>`;
  return `<div class="list-meta"><span class="result-scope">${total === 1 ? "1 result" : `${e(total)} results`}${p.get("country")?`<button class="scope-chip" data-action="all-countries" title="Remove country filter">${e(country(p.get("country")))} ${icon("close")}</button>`:""}</span><label>Sort <select id="sort" aria-label="Sort results">${options}</select></label></div>${total && listing.items.length ? `<ul class="result-list">${listing.items.map(resultRow).join("")}</ul>` : empty(emptyTitle, msg, pageView() === "watchlist" ? "bookmark" : "search", clear)}${total ? `<div class="pagination"><span>${pos}–${end} of ${total}</span><div class="pager"><button data-page="${page - 1}" aria-label="Previous page" ${page <= 1 ? "disabled" : ""}>${icon("arrowLeft")}</button><button data-page="${page + 1}" aria-label="Next page" ${page >= pages ? "disabled" : ""}>${icon("arrowRight")}</button></div></div>` : ""}`;
}
async function loadList() {
  const id = ++listEpoch,
    view = pageView();
  try {
    const data = await api("/leads?" + asListParams());
    if (id !== listEpoch || view !== pageView() || !$("#result-region")) return;
    listing = { ...data, items: items(data) };
    $("#list-count").innerHTML =
      `<span class="counter">${e(listing.total ?? listing.items.length)}</span>`;
    $("#result-region").innerHTML = resultView();
    controls();
  } catch (error) {
    if (id === listEpoch && $("#result-region"))
      $("#result-region").innerHTML =
        `<div class="panel-error"><p class="notice error">${e(error.message)}</p><button class="text-btn" data-action="retry">Retry search</button></div>`;
  }
}
async function globals() {
  const [st, src, prefs] = await Promise.allSettled([api("/stats"), api("/sources"),api("/settings")]);
  if(prefs.status==="fulfilled") preferences=prefs.value;
  if (st.status === "fulfilled") stats = st.value;
  if (src.status === "fulfilled") {
    sources = items(src.value);
    sourceError = "";
  } else sourceError = src.reason.message;
  if (st.status === "rejected") throw st.reason;
}
function pageHeading(title, desc, action = "") {
  return `<div class="page-title"><div><div class="context">HTGF research workspace</div><h1>${e(title)}</h1><p>${e(desc)}</p></div>${action ? `<div class="row-actions no-print">${action}</div>` : ""}</div>`;
}
function renderError(error) {
  main.innerHTML = `<div class="wrap page-layout">${pageHeading("Workspace unavailable", "The local service could not load this view.")}<p class="notice error">${e(error.message)}</p><button class="secondary spaced" data-action="retry">Try again</button></div>`;
}
async function render() {
  const id = ++renderEpoch;
  listEpoch++;
  const v = pageView();
  document.title =
    {
      discover: "Venture discovery",
      portfolio: "HTGF portfolio",
      watchlist: "Watchlist",
      sources: "Sources",
      activity: "Scan history",
      best: "Best Find",
    }[v] + " · FounderRadar";
  nav();
  try {
    if (relevant.includes(v)) {
      researchShell();
      await globals();
      if(id!==renderEpoch)return;
      applySavedFocus();
      $("#metrics").innerHTML=metrics();
      $("#side-rail").innerHTML=rail();
      nav();
      await loadList();
      if (id === renderEpoch && params().get("lead"))
        await openDetail(params().get("lead"), false);
    } else if (v === "sources") {
      await globals();
      const [c, u, d] = await Promise.all([
        api("/coverage"),
        api("/imports"),
        api("/duplicates"),
      ]);
      if (id !== renderEpoch) return;
      coverage = items(c);
      inbox = items(u);
      pairs = items(d);
      paintSources();
    } else if (v === "activity") {
      const [sc, ch] = await Promise.all([
        api("/scans"),
        api("/changes"),
        globals(),
      ]);
      if (id !== renderEpoch) return;
      scanRows = items(sc);
      changeRows = items(ch);
      paintHistory();
    } else if (v === "best") {
      await globals();
      if (id === renderEpoch) {
        paintReport();
        if (params().get("lead")) await openDetail(params().get("lead"), false);
      }
    } else {
      goto("discover");
    }
  } catch (err) {
    if (id === renderEpoch) renderError(err);
  }
}

function humanStatus(k) {
  return (
    {
      VERIFIED_REGISTERED: "Verified registration",
      NOT_VERIFIED: "No verified registration found",
      PENDING_REVIEW: "Pending review",
      CONFLICTING: "Conflicting evidence",
      VERIFIED_FUNDING_ANNOUNCED: "Funding publicly announced",
      NO_VERIFIED_FUNDING_FOUND: "No verified funding found",
      UNKNOWN: "Unknown",
    }[k] || keyText(k)
  );
}
function fact(k, v) {
  return `<div><dt>${e(k)}</dt><dd>${e(v ?? "Unknown")}</dd></div>`;
}
function evidenceCards(es) {
  if (!es?.length)
    return '<p class="hint">No source evidence is attached to this record.</p>';
  const timeline = [...es].sort((a, b) =>
    String(
      a.event_date || a.published_at || a.first_observed_at || "",
    ).localeCompare(
      String(b.event_date || b.published_at || b.first_observed_at || ""),
    ),
  );
  return timeline
    .map(
      (x, i) =>
        `<article class="evidence-item" id="ev-${e(x.id ?? i)}">${x.signal_type ? `<div class="eyebrow">${e(normalizeSignal(x.signal_type))}</div>` : ""}<strong>${e(x.claim || x.title || "Source evidence")}</strong>${link(x.url, x.source_name || x.title || "Original source")}${x.quote ? `<blockquote>“${e(x.quote)}”</blockquote>` : ""}<div class="evidence-dates"><span>Event ${e(date(x.event_date))}</span><span>Published ${e(date(x.published_at))}</span><br><span>First observed ${e(date(x.first_observed_at, true))}</span><span>Retrieved ${e(date(x.retrieved_at, true))}</span></div></article>`,
    )
    .join("");
}
function sourcesForTeam(team = []) {
  if (!team.length)
    return "<p>No publicly verified team members in this dossier.</p>";
  return `<ul>${team.map((t) => `<li><strong>${e(t.name)}</strong>${t.role ? ` · ${e(t.role)}` : ""} ${link(t.source_url, "Source")}</li>`).join("")}</ul>`;
}
function detailHtml(l) {
  const sc = l.scores || {},
    ev = l.evidence || [],
    scoreKeys = ["quality", "confidence", "earliness", "momentum", "priority"];
  const rubric = (sc.breakdown || [])
    .map(
      (r) =>
        `<li><strong>${e(r.label)} · ${e(r.score)}/${e(r.max)}</strong>${r.reason ? ` · ${e(r.reason)}` : ""} ${(
          r.evidence_ids || []
        )
          .filter((id) => ev.some((x) => String(x.id) === String(id)))
          .map(
            (id) =>
              `<a href="#ev-${e(id)}" data-jump="ev-${e(id)}">[Evidence]</a>`,
          )
          .join(" ")}</li>`,
    )
    .join("");
  const legal = l.legal_entity || (l.legal_entities || [])[0];
  return `<div class="sheet-top"><span>Venture dossier</span><button class="icon-btn" data-action="close-detail" aria-label="Close dossier">${icon("close")}</button></div><div class="sheet-body"><div class="sheet-identity">${mono(l.name)}<div class="sheet-heading"><h2>${e(l.name)}</h2><div class="sheet-tags">${pill(stageLabel(l.stage, l.kind), stageTone(l.stage, l.kind))}${l.sector ? pill(l.sector) : ""}</div></div></div><p class="sheet-summary">${e(l.summary || "Evidence is listed below.")}</p><div class="detail-actions"><button class="${l.watched ? "secondary" : "primary"}" data-watch="${e(l.id)}" data-watched="${Boolean(l.watched)}">${icon(l.watched ? "check" : "bookmark")}${l.watched ? "On watchlist" : "Save to watchlist"}</button><a class="secondary" href="${BASE}/exports/leads/${encodeURIComponent(l.id)}.md" download>${icon("export")}Export memo</a>${l.website && href(l.website) ? `<a class="secondary" rel="noopener noreferrer" target="_blank" href="${href(l.website)}">Website ${icon("upRight")}</a>` : ""}</div><div class="dossier-nav"><a href="#d-facts" data-jump="d-facts">Overview</a><a href="#d-evidence" data-jump="d-evidence">Evidence (${e(ev.length)})</a><a href="#d-score" data-jump="d-score">Scores</a><a href="#d-notes" data-jump="d-notes">Analyst review</a></div><section id="d-facts"><h3>Venture overview</h3><dl class="facts">${fact("Country", country(l.country) || "Unknown")}${fact("City", l.city)}${fact("University / programme", l.university)}${fact("First observed", date(l.first_observed_at, true))}${fact("Registration", humanStatus(l.registration_status))}${fact("Funding", humanStatus(l.funding_status))}${l.registered_at ? fact("Registered", date(l.registered_at)) : ""}${l.last_signal_at ? fact("Last dated signal", date(l.last_signal_at)) : ""}</dl>${Array.isArray(l.tags) && l.tags.length ? `<div class="tag-list">${l.tags.map((t) => `<span>${e(t)}</span>`).join("")}</div>` : ""}</section>${legal ? `<section><h3>Legal entity</h3><p>${e(legal.legal_name)} · ${e(legal.registration_number || legal.number || "")} ${link(legal.official_url, "Registry source")}</p></section>` : ""}${l.why_now ? `<section><h3>Why now</h3><p>${e(l.why_now)}</p></section>` : ""}${l.flags?.length ? `<section><h3>Qualification flags</h3><p>${l.flags.map(keyText).map(e).join(" · ")}</p></section>` : ""}<section><h3>Founding team</h3>${sourcesForTeam(l.team)}</section><section id="d-evidence"><h3>Evidence timeline</h3>${evidenceCards(ev)}</section><section id="d-score"><h3>Assessment</h3><div class="score-grid">${scoreKeys.map((k) => `<div><b>${score(sc[k])}</b><span class="denom"> / ${k === "earliness" ? 20 : k === "momentum" ? 15 : 100}</span><small>${label(k)}</small></div>`).join("")}</div>${sc.confidence_reason ? `<p>${e(sc.confidence_reason)}</p>` : ""}${rubric ? `<details class="spaced"><summary>View scoring evidence</summary><ul class="breakdown-list">${rubric}</ul>${sc.priority_reason ? `<p>${e(sc.priority_reason)}</p>` : ""}${sc.ceiling < 100 ? `<p>Quality capped at ${e(sc.ceiling)} with limited independent evidence.</p>` : ""}</details>` : ""}</section><section id="d-notes"><h3>Analyst review</h3><form id="review-form" class="form-grid" data-id="${e(l.id)}"><label>Decision<select name="decision">${[
    ["", "Keep current decision"],
    ["review", "Needs review"],
    ["accept", "Accept"],
    ["reject", "Reject"],
    ["watch", "Watch"],
  ]
    .map(
      ([k, v]) =>
        `<option value="${k}" ${String(l.review_status || "").toLowerCase() === k ? "selected" : ""}>${v}</option>`,
    )
    .join(
      "",
    )}</select></label><label>Private research note<textarea name="note" maxlength="4000" rows="3" placeholder="Record questions, follow-up evidence, or your next step.">${e(l.note || "")}</textarea></label><div class="form-actions"><button class="primary" type="submit">Save review</button></div></form></section></div>`;
}
let detailRequest = 0;
async function openDetail(id, push = true) {
  const token = ++detailRequest;
  if (push) setParams({ lead: id });
  $("#detail-content").innerHTML =
    `<div class="sheet-top"><span>Venture dossier</span><button class="icon-btn" data-action="close-detail" aria-label="Close dossier">${icon("close")}</button></div><div class="loading-panel" role="status">Loading evidence…</div>`;
  if (!detailDialog.open) detailDialog.showModal();
  detailDialog.scrollTop = 0;
  try {
    const l = await api("/leads/" + encodeURIComponent(id));
    if (token !== detailRequest || !detailDialog.open) return;
    activeDetail = l;
    $("#detail-content").innerHTML = detailHtml(l);
    detailDialog.scrollTop = 0;
  } catch (err) {
    if (token === detailRequest)
      $("#detail-content").innerHTML =
        `<div class="sheet-top"><span>Venture dossier</span><button class="icon-btn" data-action="close-detail" aria-label="Close dossier">${icon("close")}</button></div><div class="modal-body"><p class="notice error">${e(err.message)}</p></div>`;
  }
}
async function toggleWatch(id, watched, button) {
  button.disabled = true;
  try {
    await api("/leads/" + encodeURIComponent(id) + "/watch", {
      watched: !watched,
    });
    if (activeDetail && String(activeDetail.id) === id && detailDialog.open) {
      activeDetail.watched = !watched;
      $("#detail-content").innerHTML = detailHtml(activeDetail);
    }
    await globals();
    nav();
    if (relevant.includes(pageView()) && $("#metrics")) {
      $("#metrics").innerHTML = metrics();
      await loadList();
    }
    notify(watched ? "Removed from watchlist" : "Saved to watchlist");
  } catch (err) {
    notify(err.message);
  } finally {
    button.disabled = false;
  }
}
function paintSources() {
  main.innerHTML = `<div class="wrap page-layout">${pageHeading("Sources & coverage", "Inspect connector capabilities, source restrictions, and country coverage.", `<button class="secondary" data-action="import">${icon("plus")}Submit URL</button><button class="primary" data-action="source">${icon("layers")}Add source</button>`)}<div class="ops-tools"><div class="search-field">${icon("search")}<input id="ops-query" type="search" aria-label="Search sources and coverage" placeholder="Search countries, sources, or access modes…" value="${e(opsQuery)}"></div></div><div class="ops-tabs" aria-label="Source views"><button class="seg ${opsTab === "sources" ? "active" : ""}" data-ops-tab="sources">Source directory</button><button class="seg ${opsTab === "coverage" ? "active" : ""}" data-ops-tab="coverage">Country coverage</button><button class="seg ${opsTab === "inbox" ? "active" : ""}" data-ops-tab="inbox">URL inbox</button><button class="seg ${opsTab === "pairs" ? "active" : ""}" data-ops-tab="pairs">Match review</button><button class="seg ${opsTab==="plan"?"active":""}" data-ops-tab="plan">Research queries</button></div><div id="ops-results"></div></div>`;
  sourceRows();
}
function sourceRows() {
  const searchGroup=$("#ops-query")?.closest(".ops-tools");if(searchGroup)searchGroup.hidden=opsTab==="plan";
  if(opsTab==="plan"){paintPlanner();return}
  const lookup = opsQuery.trim().toLocaleLowerCase();
  if (opsTab === "inbox" || opsTab === "pairs") {
    reviewRows(lookup);
    return;
  }
  const list = opsTab === "coverage" ? coverage : sources;
  const found = list.filter((s) =>
    [
      s.name,
      s.kind,
      s.status,
      s.mode,
      s.country,
      country(s.country_code),
      s.notes,
    ]
      .filter(Boolean)
      .join(" ")
      .toLocaleLowerCase()
      .includes(lookup),
  );
  const loadError = opsTab === "coverage" ? coverageError : sourceError;
  const html = found
    .map(
      (s) =>
        `<tr><td><strong>${link(s.url, s.name || s.country)}</strong><p>${e(opsTab === "coverage" ? country(s.country_code) || s.country : keyText(s.kind, "Source"))}</p></td><td>${pill(sourceStatus(s), statusTone(s.status || s.mode))}${s.mode && s.mode !== s.status ? `<p>${e(keyText(s.mode))}</p>` : ""}</td><td>${e(s.notes || "No further source notes recorded.")}${s.docs_url ? `<p>${link(s.docs_url, "Official documentation")}</p>` : ""}${s.registration_date ? `<p>Registration field · ${e(s.registration_date)}</p>` : ""}${(s.id || s.source_id) === "german_register" ? `<p><button class="text-btn" data-action="registry">Record verified notice ${icon("arrow")}</button></p>` : ""}${s.id === "github" ? `<p><button class="text-btn" data-action="github">Search public repositories ${icon("arrow")}</button></p>` : ""}${s.last_error ? `<p class="notice error">${e(s.last_error)}</p>` : ""}</td>${opsTab === "sources" ? `<td>${s.last_success_at ? `<time>${e(date(s.last_success_at))}</time>` : "—"}${s.can_scan ? `<p>${s.enabled || s.id === "companies_house" ? `<button class="text-btn" data-scan-source="${e(s.id)}">Scan source ${icon("arrow")}</button>` : ""}</p><button class="source-toggle" data-switch-source="${e(s.id)}" data-enabled="${s.enabled}" aria-label="${s.enabled ? "Disable" : "Enable"} ${e(s.name)}">${s.enabled ? "Disable connector" : "Enable connector"}</button>` : ""}</td>` : ""}</tr>`,
    )
    .join("");
  $("#ops-results").innerHTML =
    `${loadError ? `<p class="notice error">${e(loadError)}</p>` : ""}<div class="table-scroll card">${found.length ? `<table class="ops-table"><thead><tr><th>${opsTab === "coverage" ? "Registry / country" : "Source"}</th><th>Capability</th><th>Coverage notes</th>${opsTab === "sources" ? "<th>Last success (UTC)</th>" : ""}</tr></thead><tbody>${html}</tbody></table>` : empty("No matching sources", lookup ? "Try another country or source name." : "No entries are available in this directory.", "layers")}</div>`;
}
function paintHistory() {
  const rows = scanRows
    .map(
      (s) =>
        `<tr><td><strong>${e(sources.find((x) => x.id === s.source_id)?.name || s.source_id || "Enabled sources")}</strong><p>${e(keyText(s.mode))}</p></td><td>${pill(keyText(s.status), statusTone(s.status))}</td><td>${e(date(s.started_at, true))}${s.completed_at ? `<p>Ended ${e(date(s.completed_at, true))}</p>` : ""}</td><td>${e(s.documents ?? 0)} docs · ${e(s.created ?? 0)} added · ${e(s.updated ?? 0)} updated${s.unchanged != null ? `<p>${e(s.unchanged)} unchanged · ${e(s.discarded ?? 0)} filtered</p>` : ""}${(s.errors || []).map((x) => `<p class="notice error">${e(typeof x === "string" ? x : x.message || JSON.stringify(x))}</p>`).join("")}</td></tr>`,
    )
    .join("");
  const changes = changeRows
    .slice(0, 40)
    .map(
      (c) =>
        `<tr><td>${c.candidate_id || c.lead_id ? `<a href="${routeLink("discover", { lead: c.candidate_id || c.lead_id })}" data-lead="${e(c.candidate_id || c.lead_id)}">${e(c.name || c.candidate_name || c.lead_name || "Open candidate")}</a>` : e(c.name || c.candidate_name || "Source record")}</td><td>${e(label(c.event_type || c.type || c.kind))}${c.detail ? `<p>${e(c.detail)}</p>` : ""}${c.mode ? `<p>${e(label(c.mode))}</p>` : ""}</td><td>${e(date(c.observed_at || c.created_at || c.at, true))}</td></tr>`,
    )
    .join("");
  main.innerHTML = `<div class="wrap page-layout">${pageHeading("Scan history", "Review collection runs and changes observed by the local index.", `<button class="secondary" data-action="retry">${icon("refresh")}Refresh</button>`)}<div class="card table-scroll">${rows ? `<table class="ops-table"><thead><tr><th>Source / mode</th><th>Result</th><th>Run time (UTC)</th><th>Changes &amp; errors</th></tr></thead><tbody>${rows}</tbody></table>` : empty("No scans recorded", "Run a bounded source scan or replay recorded evidence.", "clock", '<button class="secondary" data-action="scan">Run scan</button>')}</div><div class="section-heading"><h2>Observed changes</h2></div><div class="card table-scroll">${changes ? `<table class="ops-table"><thead><tr><th>Candidate</th><th>Change</th><th>Observed (UTC)</th></tr></thead><tbody>${changes}</tbody></table>` : empty("No changes recorded yet", "Changes appear here after the index observes new or updated evidence.", "activity")}</div></div>`;
}
function paintReport() {
  const l = stats.best_find;
  if (!l) {
    main.innerHTML = `<div class="wrap page-layout">${pageHeading("Best Find", "An analyst-selected venture with traceable evidence.")}<div class="card">${empty("No Best Find selected", "The workspace needs a reviewed candidate with source evidence.", "target")}</div></div>`;
    return;
  }
  main.innerHTML = `<div class="wrap report-layout">${pageHeading("Best Find", "Investment research brief", `<button class="secondary" data-action="print">${icon("file")}Print brief</button><a class="secondary" href="${BASE}/exports/leads/${encodeURIComponent(l.id)}.md" download>${icon("export")}Export memo</a>`)}<article class="report-card card"><div class="eyebrow">${icon("target")} Best Find · HTGF research</div><h2 class="report-title">${e(l.name)}</h2><p class="report-lede">${e(l.summary)}</p><div class="sheet-tags">${pill(stageLabel(l.stage, l.kind), stageTone(l.stage, l.kind))} ${l.country ? pill(country(l.country)) : ""} ${l.sector ? pill(l.sector) : ""}</div><div class="report-block"><h2>Investment rationale</h2><p>${e(l.best_find?.rationale || l.why_now || "Awaiting analyst review.")}</p></div>${l.why_now ? `<div class="report-block"><h2>Commercialization signal</h2><p>${e(l.why_now)}</p></div>` : ""}<div class="report-block"><h2>Team</h2>${sourcesForTeam(l.team)}</div><div class="report-block"><h2>Open questions</h2><p>${e(l.best_find?.next_check || "Verify the stage, team and current commercial milestones directly.")}</p><p class="spaced">${e(humanStatus(l.registration_status))} · ${e(humanStatus(l.funding_status))}</p></div><div class="report-block"><h2>Evidence timeline</h2>${evidenceCards(l.evidence)}</div><div class="detail-actions no-print"><a class="primary" href="${routeLink("best", { lead: l.id })}" data-lead="${e(l.id)}">Open venture dossier ${icon("arrow")}</a></div></article></div>`;
}

function popup(title, body) {
  $("#action-content").innerHTML =
    `<div class="modal-title"><h2>${e(title)}</h2><button class="icon-btn" data-action="close-popup" aria-label="Close dialog">${icon("close")}</button></div><div class="modal-body">${body}</div>`;
  actionDialog.setAttribute("aria-label", title);
  if (!actionDialog.open) actionDialog.showModal();
}
function formError(err) {
  const n = $("#form-error");
  if (n) {
    n.textContent = err.message;
    n.className = "notice error";
  } else notify(err.message);
}
const errorBox = '<div id="form-error" role="alert"></div>';
async function scanDialog(sourceId) {
  popup("Run a source scan", '<p role="status">Checking enabled sources…</p>');
  try {
    await globals();
    if (!actionDialog.open) return;
    const eligible = sources.filter(
      (s) =>
        s.can_scan &&
        (s.enabled || s.id === sourceId || s.id === "companies_house"),
    );
    if (!eligible.length) {
      popup(
        "Run a source scan",
        empty(
          "No available connectors",
          sourceError ||
            "Open the source directory to inspect access requirements.",
          "radar",
          `<a class="secondary" href="${routeLink("sources")}" data-view="sources">Inspect sources</a>`,
        ),
      );
      return;
    }
    popup(
      "Run a source scan",
      `<p>Choose a source and collection mode. Each connector limits the number of requests in a run.</p><form class="form-grid" id="scan-form"><label>Source<select name="source_id" id="scan-source">${eligible.map((s) => `<option value="${e(s.id)}" ${s.id === sourceId ? "selected" : ""}>${e(s.name)}</option>`).join("")}</select></label><label>Collection mode<select name="mode" id="scan-mode"><option value="live">Live scan</option><option value="replay">Replay recorded evidence</option></select></label><label id="scan-days">Registration window<select name="days"><option value="7">Last 7 days</option><option value="30" selected>Last 30 days</option><option value="90">Last 90 days</option></select></label><div class="notice" id="scan-desc"></div>${errorBox}<div class="form-actions"><button class="secondary" data-action="close-popup" type="button">Cancel</button><button class="primary" type="submit">${icon("radar")}Start scan</button></div></form>`,
    );
    scanHint();
  } catch (err) {
    popup("Run a source scan", `<p class="notice error">${e(err.message)}</p>`);
  }
}
function scanHint() {
  const s = sources.find((x) => x.id === $("#scan-source")?.value);
  if (!$("#scan-desc")) return;
  $("#scan-days").hidden =
    !["companies_house", "norway"].includes(s?.id) ||
    $("#scan-mode").value === "replay";
  $("#scan-desc").textContent =
    $("#scan-mode").value === "replay"
      ? "Replay reprocesses the stored public evidence for this source. It makes no live-source observations."
      : s?.notes ||
        "Fetch the source within its configured request budget. Any access errors appear in scan history.";
}
const doneScan = (status) =>
  Boolean(status) &&
  !["pending", "queued", "running", "started"].includes(status);
async function observeScan(s) {
  if (!actionDialog.open) return;
  const name =
    sources.find((src) => src.id === s.source_id)?.name ||
    s.source_id ||
    "Source";
  popup(
    "Scan progress",
    `<div class="scan-result"><strong>${e(name)}</strong>${pill(keyText(s.status), statusTone(s.status))} ${pill(keyText(s.mode))}<p>${e(s.documents ?? 0)} documents · ${e(s.created ?? 0)} added · ${e(s.updated ?? 0)} updated · ${e(s.unchanged ?? 0)} unchanged · ${e(s.discarded ?? 0)} filtered</p>${(s.errors || []).map((x) => `<p class="notice error">${e(typeof x === "string" ? x : x.message || JSON.stringify(x))}</p>`).join("")}</div><div class="form-actions"><a class="subtle" href="${routeLink("activity")}" data-view="activity">Open scan history ${icon("arrow")}</a><button data-action="close-popup" class="secondary">Close</button></div>`,
  );
  if (doneScan(s.status)) {
    if (relevant.includes(pageView())) {
      await globals();
      if ($("#metrics")) {
        $("#metrics").innerHTML = metrics();
        $("#side-rail").innerHTML = rail();
        await loadList();
      }
    } else if (pageView() === "activity") await render();
    return;
  }
  clearTimeout(scanTimer);
  scanTimer = setTimeout(async () => {
    if (!actionDialog.open) return;
    try {
      await observeScan(await api("/scans/" + encodeURIComponent(s.id)));
    } catch (err) {
      if (actionDialog.open)
        popup(
          "Scan progress",
          `<p class="notice error">${e(err.message)}</p><a data-view="activity" href="${routeLink("activity")}">Open scan history</a>`,
        );
    }
  }, 1200);
}
async function settingsDialog() {
  popup("Workspace settings", '<p role="status">Loading settings…</p>');
  try {
    const [s, directory]=await Promise.all([api("/settings"),api("/coverage")]);
    if (!actionDialog.open) return;
    popup(
      "Workspace settings",
      `<form class="form-grid" id="settings-form"><div class="form-pair"><label>Default discovery country<select name="country"><option value="">All countries</option>${items(directory).map(c=>`<option value="${e(c.country_code)}" ${c.country_code===s.country?"selected":""}>${e(c.country||country(c.country_code))}</option>`).join("")}</select></label><label>Priority threshold<input type="number" name="priority_threshold" value="${e(s.priority_threshold)}" min="0" max="100" required></label></div><label>Research keywords<input name="keywords" maxlength="500" value="${e(Array.isArray(s.keywords) ? s.keywords.join(", ") : s.keywords || "")}" placeholder="Comma-separated terms"></label><label>Scan interval in hours<input type="number" name="interval_hours" value="${e(s.interval_hours)}" min="1" max="720" required></label><label><span><input type="checkbox" name="scheduled" ${s.scheduled ? "checked" : ""}> Enable scheduled scans</span></label><p class="hint">The local scheduler must be running for scheduled scans.</p><div class="notice"><strong>Optional credentials</strong><br>Companies House · ${s.credentials?.companies_house ? "Configured" : "Key required"}<br>GitHub · ${s.credentials?.github ? "Token configured" : "No token configured"}<br>Brave Search · ${s.credentials?.brave?"Key configured":"Key required"}</div>${errorBox}<div class="form-actions"><button class="secondary" type="button" data-action="close-popup">Cancel</button><button class="primary" type="submit">Save settings</button></div></form>`,
    );
  } catch (err) {
    popup(
      "Workspace settings",
      `<p class="notice error">${e(err.message)}</p>`,
    );
  }
}
function importDialog(prefill={}) {
  popup(
    "Submit a public source URL",
    `<p>Add a professionally relevant source to the analyst review inbox.</p><form class="form-grid" id="import-form"><label>Source URL<input type="url" name="url" required maxlength="2048" value="${e(prefill.url)}" placeholder="https://…"></label><label>Title<input name="title" required maxlength="180" value="${e(prefill.title)}" placeholder="Public article, cohort, or company notice"></label><label>Research note<textarea name="note" rows="3" maxlength="2000" placeholder="What should the analyst verify?"></textarea></label>${errorBox}<div class="form-actions"><button type="button" class="secondary" data-action="close-popup">Cancel</button><button class="primary">Submit for review</button></div></form>`,
  );
}
function queryChange(changes, replace = false) {
  if("country" in changes&&!Object.hasOwn(changes,"focus"))changes.focus="off";
  filterExtrasOpen = $("#filter-extra")?.open || false;
  clearTimeout(searchTimer);
  setParams({ ...changes, page: null }, replace);
  controls();
  loadList();
}
function resetSearch() {
  filterExtrasOpen = false;
  const resets = Object.fromEntries(fields.map((k) => [k, null]));
  setParams({...resets,focus:"off"});
  $("#q").value = "";
  controls();
  loadList();
}
document.addEventListener("click", (event) => {
  const node = event.target.closest("a,button");
  if (!node) return;
  if (
    node.tagName === "A" &&
    (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey)
  )
    return;
  if (node.hasAttribute("data-view")) {
    event.preventDefault();
    goto(node.dataset.view);
    return;
  }
  if (node.hasAttribute("data-lead")) {
    event.preventDefault();
    openDetail(node.dataset.lead);
    return;
  }
  if (node.hasAttribute("data-jump")) {
    event.preventDefault();
    document
      .getElementById(node.dataset.jump)
      ?.scrollIntoView({ block: "start" });
    return;
  }
  if (node.hasAttribute("data-watch")) {
    toggleWatch(node.dataset.watch, node.dataset.watched === "true", node);
    return;
  }
  if (node.hasAttribute("data-plan-execute")){runWebQuery(node);return}
  if(node.hasAttribute("data-plan-save")){const match=planner.response?.items?.[Number(node.dataset.planSave)];if(match)importDialog(match);return}
  if (node.hasAttribute("data-switch-source")) {
    switchSource(node);
    return;
  }
  if (node.hasAttribute("data-pair")) {
    decidePair(node);
    return;
  }
  if (node.hasAttribute("data-scan-source")) {
    scanDialog(node.dataset.scanSource);
    return;
  }
  if (node.hasAttribute("data-stage")) {
    selectStage(node.dataset.stage);
    return;
  }
  if (node.hasAttribute("data-page")) {
    setParams({ page: node.dataset.page });
    loadList();
    $("#q")?.scrollIntoView({ block: "nearest" });
    return;
  }
  if (node.hasAttribute("data-ops-tab")) {
    opsTab = node.dataset.opsTab;
    paintSources();
    return;
  }
  switch (node.dataset.action) {
    case "scan":
      scanDialog();
      break;
    case "settings":
      settingsDialog();
      break;
    case "all-countries":queryChange({country:null});break;
    case "filters":
      filtersOpen = !filtersOpen;
      controls();
      break;
    case "clear":
      resetSearch();
      break;
    case "close-detail":
      detailDialog.close();
      break;
    case "close-popup":
      actionDialog.close();
      break;
    case "registry":
      registryDialog();
      break;
    case "github":
      githubDialog();
      break;
    case "source":
      newSourceDialog();
      break;
    case "import":
      importDialog();
      break;
    case "retry":
      render();
      break;
    case "print":
      window.print();
      break;
  }
});
document.addEventListener("change", (event) => {
  const node = event.target;
  if (node.id === "sort") queryChange({ sort: node.value });
  else if (node.matches("[data-filter]"))
    queryChange({ [node.dataset.filter]: node.value });
  else if (node.id === "notice-type") {
    const f = $("#registration-field");
    f.hidden = node.value !== "incorporation";
    const input = f.querySelector("input");
    input.disabled = f.hidden;
    input.required = !f.hidden;
  } else if (node.id === "scan-source" || node.id === "scan-mode") scanHint();
});
document.addEventListener("input", (event) => {
  if (event.target.id === "q") {
    const q = event.target.value;
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => queryChange({ q: q.trim() }, true), 160);
  } else if (event.target.id === "ops-query") {
    opsQuery = event.target.value;
    sourceRows();
  }
});
document.addEventListener("keydown", (event) => {
  if (
    event.key === "/" &&
    !detailDialog.open &&
    !actionDialog.open &&
    !event.target.matches("input,textarea,select,[contenteditable]") &&
    $("#q")
  ) {
    event.preventDefault();
    $("#q").focus();
  }
  if (event.key === "Enter" && event.target.id === "q") {
    event.preventDefault();
    queryChange({ q: event.target.value.trim() }, true);
  }
});
document.addEventListener("submit", async (event) => {
  const f = event.target;
  if (
    ![
      "scan-form",
      "review-form",
      "settings-form",
      "import-form",
      "source-form",
      "notice-form",
      "github-form",
      "planner-form",
    ].includes(f.id)
  )
    return;
  event.preventDefault();
  const data = new FormData(f),
    button = event.submitter || f.querySelector("[type=submit]");
  if (button) button.disabled = true;
  try {
    if (f.id === "scan-form") {
      const run = await api("/scans", {
        source_id: data.get("source_id"),
        mode: data.get("mode"),
        days: Number(data.get("days") || 30),
      });
      await observeScan(run);
    } else if (f.id === "settings-form") {
      const oldFocus=preferences.country;
      preferences=await api("/settings", {
        country: String(data.get("country") || "")
          .trim()
          .toUpperCase(),
        priority_threshold: Number(data.get("priority_threshold")),
        keywords: String(data.get("keywords") || "").trim(),
        interval_hours: Number(data.get("interval_hours")),
        scheduled: data.has("scheduled"),
      });
      actionDialog.close();
      if(oldFocus!==preferences.country&&pageView()==="discover"){setParams({country:null,focus:null,page:null},true);await render()}
      notify("Workspace settings saved");
    } else if (f.id === "review-form") {
      const decision = data.get("decision"),
        note = data.get("note") || "";
      await api("/leads/" + encodeURIComponent(f.dataset.id) + "/review", {
        note,
        ...(decision ? { decision } : {}),
      });
      notify("Research review saved");
      if (activeDetail) {
        activeDetail.note = note;
        if (decision) activeDetail.review_status = decision;
      }
      await globals();
      nav();
      if ($("#metrics")) {
        $("#metrics").innerHTML = metrics();
        await loadList();
      }
    } else if (f.id === "notice-form") {
      const notice = Object.fromEntries(data);
      notice.verified = data.has("verified");
      for (const key of ["registered_at", "published_at"])
        if (!notice[key]) delete notice[key];
      const lead = await api("/registry-notice", notice);
      actionDialog.close();
      await openDetail(lead.id);
      notify("Verified notice recorded");
    } else if (f.id === "planner-form") {await buildPlan(data)} else if (f.id === "github-form") {
      await githubResults(String(data.get("q") || "").trim());
    } else if (f.id === "source-form") {
      await api("/sources", {
        name: data.get("name"),
        url: data.get("url"),
        notes: data.get("notes") || "",
      });
      actionDialog.close();
      opsTab = "sources";
      await render();
      notify("Source added to directory");
    } else if (f.id === "import-form") {
      await api("/import-url", {
        url: data.get("url"),
        title: data.get("title"),
        note: data.get("note") || "",
      });
      actionDialog.close();
      if(opsTab!=="plan")opsTab = "inbox";
      await render();
      notify("URL added to the review inbox");
    }
  } catch (err) {
    formError(err);
  } finally {
    if (button) button.disabled = false;
  }
});
detailDialog.addEventListener("close", () => {
  detailRequest++;
  activeDetail = null;
  if (params().has("lead")) setParams({ lead: null }, true);
});
actionDialog.addEventListener("close", () => {
  clearTimeout(scanTimer);
});
for (const dialog of [detailDialog, actionDialog])
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) {
      const r = dialog.getBoundingClientRect();
      if (
        event.clientX < r.left ||
        event.clientX > r.right ||
        event.clientY < r.top ||
        event.clientY > r.bottom
      )
        dialog.close();
    }
  });
window.addEventListener("popstate", () => {
  clearTimeout(searchTimer);
  if (!params().get("lead") && detailDialog.open) detailDialog.close();
  filtersOpen = filterCount() > 0;
  render();
});
let resizeTimer;
window.addEventListener("resize", () => {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => paintMap($("#radar-map")), 70);
});
filtersOpen = filterCount() > 0;
render();

function reviewRows(lookup) {
  const via = (s) => s.toLowerCase().includes(lookup);
  if (opsTab === "inbox") {
    const rows = inbox
      .filter((item) => via([item.title, item.url, item.note].join(" ")))
      .map(
        (item) =>
          `<tr><td><strong>${link(item.url, item.title || "Submitted page")}</strong></td><td>${e(item.note || "—")}</td><td>${e(date(item.observed_at, true))}</td></tr>`,
      )
      .join("");
    $("#ops-results").innerHTML =
      `<div class="table-scroll card">${rows ? `<table class="ops-table"><thead><tr><th>Submitted URL</th><th>Analyst note</th><th>Observed (UTC)</th></tr></thead><tbody>${rows}</tbody></table>` : empty(lookup ? "No matching URLs" : "Your source inbox is empty", "Submit public URLs for follow-up research.", "book", '<button class="secondary" data-action="import">Submit URL</button>')}</div>`;
    return;
  }
  const list = pairs.filter((p) =>
    via([p.left?.name, p.right?.name, p.reason, p.decision].join(" ")),
  );
  $("#ops-results").innerHTML = list.length
    ? list
        .map((p) => {
          const member = (l) =>
            l
              ? `<div class="pair-member"><a href="${routeLink("discover", { lead: l.id })}" data-lead="${e(l.id)}"><strong>${e(l.name)}</strong></a><small>${e([country(l.country), l.sector].filter(Boolean).join(" · "))}</small><p>${e(l.summary || "")}</p>${link(l.evidence?.[0]?.url, "Review source")}</div>`
              : "";
          return `<article class="card pair-card"><div class="pair-members">${member(p.left)}${member(p.right)}</div><p class="hint">${e(p.reason || p.explanation || "Potential identity match.")}</p><div class="detail-actions">${pill(keyText(p.decision || "pending"))}${[
            "related",
            "distinct",
            "pending",
          ]
            .filter((d) => d !== p.decision)
            .map(
              (d) =>
                `<button class="secondary" data-pair="${e(d)}" data-left="${e(p.left_id)}" data-right="${e(p.right_id)}">${d === "related" ? "Mark related" : d === "distinct" ? "Mark distinct" : "Reopen"}</button>`,
            )
            .join("")}</div></article>`;
        })
        .join("")
    : `<div class="card">${empty("No candidate matches to review", lookup ? "Try a different venture name." : "Potential duplicate records appear here with side-by-side evidence.", "layers")}</div>`;
}
async function switchSource(button) {
  const enabled = button.dataset.enabled !== "true";
  button.disabled = true;
  try {
    await api("/sources/" + encodeURIComponent(button.dataset.switchSource), {
      enabled,
    });
    sources = items(await api("/sources"));
    sourceRows();
    notify(enabled ? "Connector enabled" : "Connector disabled");
  } catch (err) {
    notify(err.message);
  } finally {
    button.disabled = false;
  }
}
async function decidePair(button) {
  button.disabled = true;
  try {
    await api("/duplicates", {
      left_id: button.dataset.left,
      right_id: button.dataset.right,
      decision: button.dataset.pair,
    });
    pairs = items(await api("/duplicates"));
    sourceRows();
    notify("Match review saved");
  } catch (err) {
    notify(err.message);
  } finally {
    button.disabled = false;
  }
}
function newSourceDialog() {
  popup(
    "Add a manual research source",
    `<p>Register a public page for analyst review. It will appear in the source directory with manual access.</p><form class="form-grid" id="source-form"><label>Source name<input name="name" required maxlength="140"></label><label>Public URL<input type="url" name="url" required maxlength="2048" placeholder="https://…"></label><label>Coverage notes<textarea name="notes" rows="3" maxlength="1500"></textarea></label>${errorBox}<div class="form-actions"><button type="button" class="secondary" data-action="close-popup">Cancel</button><button class="primary">Add source</button></div></form>`,
  );
}

function registryDialog() {
  popup(
    "Record a German registry notice",
    `<p>Transcribe the public notice you verified in the German commercial register. An initial entry requires its explicit registration date.</p><form id="notice-form" class="form-grid"><label>Legal name<input name="name" required maxlength="300"></label><div class="form-pair"><label>Register court<input name="court" required maxlength="100"></label><label>Register number<input name="registration_number" required maxlength="50" placeholder="HRB …"></label></div><label>Public register URL<input type="url" name="official_url" required maxlength="1200"></label><label>Type of notice<select name="event_type" id="notice-type">${["incorporation", "amendment", "relocation", "branch", "publication", "unknown"].map((x) => `<option value="${x}">${label(x)}</option>`).join("")}</select></label><div class="form-pair"><label id="registration-field">First registration date<input type="date" name="registered_at" required></label><label>Published date, if known<input type="date" name="published_at"></label></div><label>Supporting excerpt<textarea name="quote" rows="2" required maxlength="450"></textarea></label><label><span><input type="checkbox" name="verified" required> I checked the official document and its notice type.</span></label>${errorBox}<div class="form-actions"><button type="button" class="secondary" data-action="close-popup">Cancel</button><button type="submit" class="primary">Record notice</button></div></form>`,
  );
}
function githubDialog() {
  popup(
    "Research public repositories",
    `<p>Search public GitHub repositories for technical evidence. Check the venture association independently before using a result.</p><form id="github-form" class="form-grid"><label>Repository query<input name="q" required minlength="4" maxlength="120" placeholder="Project or technology name"></label>${errorBox}<div class="form-actions"><button type="submit" class="primary">${icon("search")}Search GitHub</button></div></form><div id="github-results" aria-live="polite"></div>`,
  );
}
async function githubResults(q) {
  const region = $("#github-results");
  region.innerHTML =
    '<div class="loading-panel">Searching public repositories…</div>';
  const data = await api("/developer/github?" + new URLSearchParams({ q }));
  if (!region.isConnected) return;
  region.innerHTML = `${(data.errors || []).map((x) => `<p class="notice error">${e(x)}</p>`).join("")}${(data.records || []).length ? data.records.map((item) => `<article class="repository"><strong>${link(item.url, item.repo)}</strong><p>${e(item.description)}</p><small>${item.license ? `${e(item.license)} · ` : ""}Updated ${e(date(item.pushed_at))}</small></article>`).join("") : data.errors?.length ? "" : empty("No matching repositories", "Try a different project name or technology.", "search")}`;
}

function applySavedFocus(){
  if(pageView()!=="discover")return;
  const p=params();
  const focus=preferences.country?.toUpperCase();
  if(p.get("focus")==="off"||(p.has("country")&&p.get("focus")!=="default"))return;
  if(p.get("stage")==="NEWLY_INCORPORATED"||p.get("scope")==="all"){
    if(p.get("focus")==="default")setParams({country:null,focus:"auto-suspended"},true);
    return;
  }
  if(focus&&focus!=="ALL")setParams({country:focus,focus:"default"},true);
  else if(p.get("focus")==="default")setParams({country:null,focus:null},true);
}
function selectStage(stage){
  const changes={stage,days:null};
  const focus=params().get("focus");
  if(stage==="NEWLY_INCORPORATED"&&focus==="default"){changes.country=null;changes.focus="auto-suspended"}
  if(stage!=="NEWLY_INCORPORATED"&&focus==="auto-suspended"&&preferences.country&&preferences.country!=="ALL"){
    changes.country=preferences.country;changes.focus="default";
  }
  queryChange(changes);
}
function paintPlanner(){
  const chosen=planner.country||preferences.country||"DE";
  const scopes=coverage.length?coverage:[{country_code:"DE",country:"Germany"}];
  const opts=scopes.map(c=>`<option value="${e(c.country_code)}" ${c.country_code===chosen?"selected":""}>${e(c.country||country(c.country_code))}</option>`).join("");
  const suggested=planner.items.map((item,i)=>`<li><div><strong>${e(item.query)}</strong><small>${e([item.language?.toUpperCase(),label(item.scope)].filter(Boolean).join(" · "))}</small></div><button class="text-btn" data-plan-execute="${i}">${icon("search")}Run web search</button></li>`).join("");
  const result=planner.response;
  const hits=result?.items?.map((hit,i)=>`<li><div><strong>${link(hit.url,hit.title||"Search result")}</strong><p>${e(hit.description)}</p></div><button class="text-btn" data-plan-save="${i}">${icon("plus")}Submit URL</button></li>`).join("");
  $("#ops-results").innerHTML=`<section class="card plan-card"><h2>Research query planner</h2><p class="hint">Generate country-specific searches for public founder signals. Web search requires an optional Brave Search API key.</p><form id="planner-form" class="plan-controls"><label>Country<select name="country" required>${opts}</select></label><label>Technology<input name="technology" required maxlength="100" value="${e(planner.technology)}" placeholder="e.g. robotics"></label><button class="primary" type="submit">Generate queries</button></form>${planner.feedback?`<p class="notice error">${e(planner.feedback)}</p>`:""}${suggested?`<h3>Suggested searches</h3><ul class="plan-list">${suggested}</ul>`:planner.ready?empty("No suggestions available","Try a different technology or country.","search"):""}${result?`<section class="web-results" aria-live="polite"><div class="rail-head"><h3>Web search results</h3>${pill(keyText(result.status),statusTone(result.status))}</div><p class="hint">${e(planner.query)}</p>${result.message?`<p class="notice">${e(result.message)}</p>`:""}${hits?`<ul class="plan-list">${hits}</ul>`:!result.message?'<p class="hint">No matching public URLs were returned.</p>':""}<button class="subtle" data-action="import">${icon("plus")}Submit a public URL manually</button></section>`:""}</section>`;
}
async function buildPlan(form){
  const selected=String(form.get("country")||"DE"),tech=String(form.get("technology")||"").trim();
  try{
    const data=await api("/discovery/plan?"+new URLSearchParams({country:selected,technology:tech,limit:"14"}));
    planner={country:selected,technology:tech,generatedCountry:selected,items:items(data),ready:true,configured:data.configured,query:"",response:null,feedback:""};
  }catch(err){planner.feedback=err.message}
  if(pageView()==="sources"&&opsTab==="plan")paintPlanner();
}
async function runWebQuery(button){
  const item=planner.items[Number(button.dataset.planExecute)];if(!item)return;
  button.disabled=true;button.textContent="Searching…";planner.query=item.query;
  try{planner.response=await api("/discovery/web",{query:item.query,country:planner.generatedCountry||planner.country});planner.feedback=""}
  catch(err){planner.response={status:"failed",message:err.message,items:[]}}
  if(pageView()==="sources"&&opsTab==="plan"){paintPlanner();$(".web-results")?.scrollIntoView({block:"nearest"})}
}

