# API reference

Interactive documentation is at http://127.0.0.1:8766/docs. OpenAPI is at /openapi.json. JSON mutations require a same-origin or non-browser local caller, application/json, and at most 32 KiB.

| Route | Behavior |
| --- | --- |
| GET /health | Database readiness and version |
| GET /api/v1/stats | Stored aggregate counts and Best Find |
| GET /api/v1/leads or /search | Text, collection, stage, location, sector, source, quality/confidence, publication/observation dates, review/watch, sorting and pagination |
| GET /api/v1/leads/{id} | Dossier, evidence, team, scores and analyst state |
| GET /api/v1/leads/{id}/timeline | Source events and engine observations |
| POST /api/v1/leads/{id}/watch | Boolean watched |
| POST /api/v1/leads/{id}/review | Optional decision and note |
| GET/POST /api/v1/sources | Source directory and manually registered public source |
| POST /api/v1/sources/{id} | Enable or disable an implemented adapter |
| GET /api/v1/coverage | Country capability directory |
| POST /api/v1/scans | source_id, mode live/replay, optional days 7/30/90; returns job with 202 |
| GET /api/v1/scans or /scans/{id} | Run history and result |
| GET /api/v1/changes | Recorded field/evidence changes |
| GET/POST /api/v1/settings | Local preferences and credential presence |
| POST /api/v1/import-url | Public URL, title, note into analyst inbox |
| GET /api/v1/imports | Manual inbox |
| GET/POST /api/v1/duplicates | Conservative identity proposals and related/distinct/pending decisions |
| POST /api/v1/registry-notice | Analyst-verified German register notice |
| GET /api/v1/developer/github?q= | Bounded technical repository search |
| GET /api/v1/discovery/plan | Offline multilingual query preview |
| POST /api/v1/discovery/web | Explicit optional Brave search, transient results |
| GET /api/v1/evaluation | Unknown-aware metrics and human-labelled precision |
| GET /api/v1/exports/leads.csv | Filtered safe spreadsheet export |
| GET /api/v1/exports/leads/{id}.md | Attributed investment-research memo |

Lead list responses include items, total, page, limit, facets and stage_counts. The maximum limit is 100. Country values use ISO alpha-2 codes. kind accepts prospect, portfolio or all. Text queries use AND token-prefix matching with accent folding.

Source failures are visible in terminal job statuses, errors and source health. Recorded replay operates on captured observations. It never substitutes current time for source publication or initial engine observation.
