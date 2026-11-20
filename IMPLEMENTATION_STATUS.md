# Implementation status

Verified 20 November 2026. A working single-user local MVP is delivered. The broader multi-country production roadmap remains partial.

| Feature | Status | Observed evidence and remaining work |
| --- | --- | --- |
| Local app and search | DONE | FastAPI/Pydantic + browser frontend, SQLite FTS5/fallback, filters, sort, capped pagination. Browser robotics search returns 20 HTGF entries. |
| Relational storage and migration | DONE | Runnable Alembic migration, WAL, transactions, foreign keys, scan reservation and idempotence tests. |
| Real recorded dataset | DONE | 568 ventures, 605 evidence/signals, 571 documents, 11 legal entities. All evidence has source and capture provenance. |
| HTGF portfolio | PARTIAL | 541 public English entries, 490 taxonomies, 21 business descriptions, 14 sourced sites. Other fields remain unknown. Includes historical investments and exits. |
| Three discovery feeds | DONE | 10 potential pre-company, 11 registry-confirmed recent companies, six existing/emerging prospects. Commercial relevance requires its own evidence. |
| Live sources | DONE | HTGF 541, TUM 10, KIT 6 and Norway eight records actually retrieved. TUM browser scan showed live success, 10 unchanged, no duplicates. |
| Evidence timeline/team/scores | DONE | Cited professional team information, separate dates, deterministic quality and confidence, evidence IDs for positive scores. |
| Best Find | DONE | IsoSphere, five observations/four publishers. Paid-pilot conversion, legal identity and equity funding require diligence. |
| Watch/notes/reviews/exports | DONE | Persistent analyst state, audit records, filtered safe CSV and sourced Markdown memo. |
| Country/campus coverage | PARTIAL | 49 jurisdictions with capability labels and 20 verified manual campus resources. Two automated university sources. Most country adapters await implementation. |
| Companies House | PARTIAL | Tested authenticated adapter and three real public page records. Live API query awaits COMPANIES_HOUSE_API_KEY. |
| Estonia | PARTIAL | Bounded CSV/ZIP importer and delta/date tests. Production official snapshot yet to be supplied. CLI output can be converted/ingested programmatically. |
| Germany register | PARTIAL | Validated manual official-notice intake. No automated portal scanner. |
| GitHub | PARTIAL | Actual public repo search succeeded. Venture matching remains manual. Hugging Face planned. |
| Social/event discovery | PARTIAL | Manual public URL inbox and platform capability labels. Automated social/event feeds await permitted interfaces. |
| Multilingual web discovery | PARTIAL | Offline seven-language query planner, optional bounded Brave adapter tested with mocks. Live search awaits BRAVE_SEARCH_API_KEY. |
| Source controls/history | DONE | Enable switches, manual source addition, errors, actual job history and changes. |
| Entity resolution | PARTIAL | Stable IDs, shared-URL/country proposals, reversible pair decisions. Full merge/split and fuzzy matching remain future work. |
| Scheduler | PARTIAL | Disabled-by-default settings, separate local schedule client, single-active-scan guard. One API worker and one scheduler supported. Multi-scheduler leases remain future work. |
| Network/export safeguards | DONE | Fixed public hosts, DNS-pinned TLS, robots checks, timeouts/body limits, escaped text, CSV protection, JSON size/origin/host checks. |
| Retry/cache | PARTIAL | Official APIs use bounded retries. Website cache supports in-process conditional requests. Website failures remain visible. Persistent caching and broader retry coverage remain future work. |
| Evaluation | PARTIAL | Denominator-aware metrics, ten-project assistant desk review. Human-labelled precision is unknown until analyst labels are added. |
| Removal/retention | PARTIAL | Backup-first removal utility and ID suppression, ingestion suppression tested. Packaged recordings/exports require review. Automated retention remains future work. |
| Production architecture | PARTIAL | FastAPI/Pydantic, Alembic/SQLAlchemy migration, SQLite and vanilla browser modules. React/TypeScript, PostgreSQL and shared-user authentication remain future work. |

## Executed checks

- Backend pytest suite passed 49 tests and 12 subtests. One upstream Starlette/httpx deprecation warning remains visible.
- Frontend Node test suite passed eight checks, including seven behavioral subtests. It exercises actual handlers with an isolated DOM adapter.
- Ruff correctness checks passed across backend, collectors, registries, scripts, tests and launcher.
- Runtime smoke check passed health, statistics, robotics search, 34 sources, 49 countries, evaluation and 14 query previews.
- Actual browser checks covered portfolio search, source dossier, Best Find, source scan and responsive layout. At 390px viewport, DOM client and scroll widths both measured 390px.
- The TUM scan displayed zero created, zero updated, 10 unchanged. Its 13 document references include historical supporting sources retained in the bundle. Documents processed and outbound HTTP requests have different denominators.
- Repeated live/replay intake of the 557 directory records produced zero duplicated candidates or evidence.
- The automated suite covers priority pipeline, provenance, security, date, classification and persistence regressions. Some additional combinations in the original test matrix remain unimplemented.

## Data interpretation and next extension

The 27 prospects include three verified German locations, three UK companies, eight Norwegian companies and 13 unknown locations. Clear the default Germany chip to include all locations. University affiliation alone supplies no verified headquarters location.

The strongest evidence-backed sourcing candidate is IsoSphere. Earliest engine observations are from November 2026, with older source publications found retrospectively. No comparative first appearance in commercial startup databases has been verified.

The highest-value next extension is a third automated German university programme source and a primary-source legal/paid-pilot diligence pass for the strongest prospects. Authentication and PostgreSQL support should precede shared deployment.
