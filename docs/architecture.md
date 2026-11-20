# Architecture

FastAPI and Pydantic serve a static browser-module frontend and typed HTTP API. SQLite stores ventures, source documents, evidence, signals, legal identities, review decisions, change events, scans, preferences and manual intake. SQLAlchemy runs the Alembic migration. SQLite WAL, foreign keys, parameterized queries, transaction-per-batch ingestion and FTS5 support local research. Text search has a fallback when FTS5 is unavailable.

The default startup needs the locked Python dependencies. A separate frontend toolchain is unnecessary. The implementation uses vanilla JavaScript modules and SQLite-specific persistence. React/TypeScript/Vite and PostgreSQL are extensions to the current edition.

Source adapters emit attributable records. The pipeline validates provenance, applies conservative classification, upserts official identities and records semantic changes. Evidence IDs are stable. Exact replay preserves original observation dates and analyst decisions. Source metadata and evidence timestamps remain distinct.

A single API process reserves one active scan in the database and executes it in a background worker. The optional scheduler client uses the same API. One API worker and one scheduler process are supported. Scheduling remains disabled by default.

The original source recording remains a dated input. Live refresh can add later evidence. Manual URL inbox and duplicate relationships require analyst review. Name similarity alone triggers no automatic merger. The system currently proposes same-country shared-domain relationships and stores reversible review decisions.
