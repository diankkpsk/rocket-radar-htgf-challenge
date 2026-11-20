# FounderRadar

A local venture research workspace for HTGF sourcing. Search a recorded public portfolio, discover named university venture teams, inspect source evidence, review fresh registration records, and maintain a watchlist.

The bundled recording was collected on 20 November 2026. It contains 568 attributed records and 605 evidence items. There are 541 HTGF portfolio comparables and 27 prospects, covering 10 potential pre-company teams, six existing/emerging ventures, and 11 registry-confirmed recent companies. These are sourcing candidates requiring diligence. The portfolio includes historical investments and exits. Each source's capture and field coverage is documented in SOURCES.md.

## Start

Python 3.12 or later is required. From this folder run the following.

```sh
python3 run.py
```

Open http://127.0.0.1:8766/. The launcher creates a local virtual environment and installs requirements.lock on first use if its runtime is missing. Internet access is needed for that installation. A prepared virtual environment already exists in this delivered folder. Use the following command to reuse it directly.

```sh
.venv/bin/python run.py
```

Startup applies the Alembic migration and loads the dated real-source recording. Subsequent startup preserves analyst work. Database files are stored under var/. Search, dossiers, CSV, notes, watchlists and recorded replay work offline after installation.

Port 8766 was selected because an earlier development process still occupies 8765. To choose another port use `python3 run.py --port 8770`. Stop the foreground server with Ctrl+C. Copy .env.example to .env for local configuration. Keys belong in that local file or environment variables.

## Research workflow

- HTGF portfolio searches all 541 English-language entries in the public WordPress collection. Searches match names, sector/focus tags and any captured profile evidence. Taxonomy is present on 490 records, 21 have business descriptions, and 14 have explicitly sourced websites. Country, team and other absent fields stay unknown.
- Discovery defaults to verified German locations. Remove the Germany chip to include candidates with other or unknown locations. Affiliation with TUM alone supplies no verified headquarters location.
- The three feeds distinguish potential formation signals, verified recent legal formations, and established ventures with commercial activity. Registration windows use official dates. A registration carries a low venture quality score until commercial evidence supports a stronger assessment.
- Open a dossier for publication, event, first-observation and retrieval dates, founders where cited, an evidence timeline and score explanations.
- Save to watchlist, add a private research note, and record an accept/reject/review decision. Filtered CSV and a one-candidate Markdown memo can be exported.
- Sources shows capability states, country coverage, 20 manually verified campus resources, manual URL inbox, proposed matches and research query previews. Public links added to the inbox await analyst verification.
- Scan history shows actual source runs and changes. Run scan offers live collection or replay. The source ID and mode remain visible throughout.

The Best Find brief highlights IsoSphere Technologies using TUM, a published founder interview, MIT's prize programme and BayStartUP. TUM reports more than 60 customer interviews and 14 letters of intent. Confirm conversion to paid pilots, production readiness, legal identity and equity financing during diligence. Source verification dates are available in the dossier. See docs/evaluation.md for an assistant desk review of ten projects.

## Sources and optional credentials

| Capability | Default behavior | Optional credential |
| --- | --- | --- |
| HTGF portfolio | Bounded public collection, tested live | None |
| TUM IDEAward | Named finalists and evidence, tested live | None |
| KIT Forge | Six founder interviews, tested live | None |
| Norway Brønnøysund | Official date/industry-limited company search, tested live | None |
| UK Companies House | Three attributed page recordings, tested adapter and visible key requirement | COMPANIES_HOUSE_API_KEY |
| Estonia | Bounded local snapshot parser/import CLI | An official local snapshot |
| Germany | Analyst-verified official notice intake | None |
| GitHub | On-demand public repository research, tested live | GITHUB_TOKEN can increase permitted API capacity |
| Web search | Seven-language offline query planner, optional bounded Brave API | BRAVE_SEARCH_API_KEY |

Brave search displays transient results for manual review. Its authenticated integration has mocked contract coverage and awaits a configured key for live verification. GitHub results supply technical signals. A repository author is never automatically named as a founder.

The country directory includes EU and associated European markets with per-source status. Most entries are research starting points requiring access and licensing verification. LinkedIn, Instagram and Facebook use manual professional links. Hugging Face and Hacker News connectors remain planned.

## Commands

```sh
# Explicit installation
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock

# Initialize without starting the server
.venv/bin/python run.py --init

# Run backend and static frontend together
.venv/bin/python run.py

# Offline regression and frontend behavior checks
.venv/bin/python -m pytest -q
node --test frontend/tests/workspace.test.mjs
.venv/bin/ruff check --select E9,F63,F7,F82 backend collectors registries tests run.py

# Inspect official adapters
.venv/bin/python -m registries norway --days 30 --page-size 8
.venv/bin/python -m registries uk --days 7
.venv/bin/python -m registries estonia --help

# Run optional scheduler client while the API is running
.venv/bin/python run.py --scheduler --port 8766
```

Enable scheduling in Workspace settings and keep the scheduler process running. The API uses a database reservation to allow one scan at a time. One HTTP worker and one scheduler process are supported. Settings by themselves do not start a background process. Existing in-process source caches are bounded and lost on restart.

Run a bounded live scan and inspect its result through the UI, or through the following API calls.

```sh
curl -H 'Content-Type: application/json' -d '{"source_id":"tum","mode":"live"}' http://127.0.0.1:8766/api/v1/scans
curl http://127.0.0.1:8766/api/v1/scans
curl 'http://127.0.0.1:8766/api/v1/leads?source=tum&limit=20'
```

## Architecture and API

FastAPI and Pydantic serve a same-origin JavaScript frontend. SQLite provides relational persistence, transactions, WAL and FTS5, with a text-search fallback. SQLAlchemy connects Alembic migrations. Application persistence uses readable parameterized SQLite queries. A separate frontend compilation is unnecessary. This implementation uses vanilla browser modules in place of React/Vite and currently supports SQLite databases. PostgreSQL portability and multi-user authentication are future work.

OpenAPI documentation is served at /docs and the schema at /openapi.json. Common routes include /health, /api/v1/leads, /api/v1/search, /api/v1/stats, /api/v1/sources, /api/v1/coverage, /api/v1/scans, /api/v1/changes, /api/v1/evaluation and /api/v1/exports/leads.csv. See docs/api-reference.md.

Scoring is deterministic. Quality and confidence remain distinct, and every positive quality component cites evidence IDs. A weak single-source record has a quality ceiling. The rubric is an analyst heuristic, with evaluation precision left unknown until explicit accept/reject labels cover the ranked set.

## Extending sources

Use Add source to register another official university page for manual review. Automatic extraction requires a publisher-specific adapter, explicit host allowlisting, policy checks, fixtures and parser validation. Add it to collectors/ and the source registry in backend/store.py, then test a bounded live run and record its provenance in SOURCES.md.

Registry additions belong under registries/. Verify current documentation, access rights, date semantics, pagination and error behavior first. Return legal evidence with a country and unique official ID. Update the capability directory, and use to_record to preserve the distinction between an original registration and amendments, relocations or branches.

## Limits and troubleshooting

The delivered scope is a single-user local MVP. It has no shared accounts or cloud deployment. Keep the server bound to loopback. The 568 records are a dated capture, and source scans refresh implemented adapters. Unknown registration or funding retains an explicit unknown state. Pre-company means a commercial formation signal with registration unestablished.

TUM year changes, KIT editorial changes and upstream API changes can require parser maintenance. Sources fail visibly and retain the previously collected evidence. Live scans use fixed publishers, DNS validation, request budgets, size limits, timeouts and robots checks. Website collection fails immediately on a rate limit. Official API retries are bounded. Parser and HTTP coverage does not include every combination in the original brief.

If installation cannot reach the package registry, reuse the prepared environment. If a source fails, inspect Scan history and SOURCES.md. If a source requires a key, configure it locally and restart. The frontend and API share a port and require no CORS setup. To move the database, set FOUNDER_RADAR_DB to a writable absolute path. DATABASE_URL currently accepts SQLite URLs only.

Current implementation status, known gaps, test evidence and next extensions appear in IMPLEMENTATION_STATUS.md. Source terms, retention and removal procedures appear in SECURITY_AND_DATA_POLICY.md.

For a verified removal request, inspect the candidate ID and run the removal utility with that ID. It creates a recoverable backup and suppresses future rediscovery of the same ID. Review packaged recordings and previous exports before sharing them again.

```sh
.venv/bin/python scripts/remove-candidate.py CANDIDATE_ID
```
