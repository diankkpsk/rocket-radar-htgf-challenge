CREATE TABLE sources(
 id TEXT PRIMARY KEY, name TEXT NOT NULL, kind TEXT NOT NULL, mode TEXT NOT NULL,
 status TEXT NOT NULL, url TEXT NOT NULL, notes TEXT NOT NULL, enabled INTEGER NOT NULL DEFAULT 0,
 can_scan INTEGER NOT NULL DEFAULT 0, last_attempt_at TEXT, last_success_at TEXT, last_error TEXT
);
CREATE TABLE ventures(
 id TEXT PRIMARY KEY, name TEXT NOT NULL, normalized_name TEXT NOT NULL, kind TEXT NOT NULL,
 stage TEXT NOT NULL, country TEXT, sector TEXT, website TEXT, payload TEXT NOT NULL,
 content_hash TEXT NOT NULL, first_observed_at TEXT NOT NULL, last_verified_at TEXT NOT NULL
);
CREATE INDEX venture_feed ON ventures(kind,stage,country,sector);
CREATE INDEX venture_name ON ventures(normalized_name);
CREATE TABLE documents(
 id TEXT PRIMARY KEY, source_id TEXT NOT NULL, url TEXT NOT NULL, title TEXT NOT NULL,
 content_hash TEXT NOT NULL, published_at TEXT, first_observed_at TEXT NOT NULL,
 retrieved_at TEXT NOT NULL, last_changed_at TEXT NOT NULL, provenance TEXT NOT NULL, UNIQUE(source_id,url)
);
CREATE TABLE evidence(
 id TEXT PRIMARY KEY, candidate_id TEXT NOT NULL REFERENCES ventures(id) ON DELETE CASCADE,
 document_id TEXT NOT NULL REFERENCES documents(id), source_id TEXT NOT NULL, evidence_json TEXT NOT NULL,
 identity TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1, UNIQUE(candidate_id,identity)
);
CREATE INDEX evidence_candidate ON evidence(candidate_id,active);
CREATE TABLE signals(
 id TEXT PRIMARY KEY, candidate_id TEXT NOT NULL REFERENCES ventures(id) ON DELETE CASCADE,
 evidence_id TEXT NOT NULL REFERENCES evidence(id) ON DELETE CASCADE, type TEXT NOT NULL,
 event_date TEXT, first_observed_at TEXT NOT NULL
);
CREATE TABLE legal_entities(
 id TEXT PRIMARY KEY, country_code TEXT NOT NULL, registry TEXT NOT NULL, registration_number TEXT NOT NULL,
 registered_at TEXT, official_url TEXT NOT NULL, payload TEXT NOT NULL, UNIQUE(country_code,registry,registration_number)
);
CREATE TABLE legal_links(
 candidate_id TEXT NOT NULL REFERENCES ventures(id) ON DELETE CASCADE, legal_id TEXT NOT NULL REFERENCES legal_entities(id),
 PRIMARY KEY(candidate_id,legal_id)
);
CREATE TABLE review_state(
 candidate_id TEXT PRIMARY KEY REFERENCES ventures(id) ON DELETE CASCADE,
 watched INTEGER NOT NULL DEFAULT 0, note TEXT NOT NULL DEFAULT '', decision TEXT NOT NULL DEFAULT 'unreviewed'
);
CREATE TABLE reviews(
 id INTEGER PRIMARY KEY, candidate_id TEXT NOT NULL REFERENCES ventures(id) ON DELETE CASCADE,
 decision TEXT, note TEXT, at TEXT NOT NULL
);
CREATE TABLE changes(
 id INTEGER PRIMARY KEY, candidate_id TEXT NOT NULL REFERENCES ventures(id) ON DELETE CASCADE,
 kind TEXT NOT NULL, observed_at TEXT NOT NULL, mode TEXT NOT NULL, detail TEXT NOT NULL
);
CREATE INDEX changes_time ON changes(observed_at);
CREATE TABLE scans(
 id TEXT PRIMARY KEY, source_id TEXT NOT NULL, mode TEXT NOT NULL, status TEXT NOT NULL,
 started_at TEXT NOT NULL, completed_at TEXT, created INTEGER DEFAULT 0, updated INTEGER DEFAULT 0,
 unchanged INTEGER DEFAULT 0, documents INTEGER DEFAULT 0, discarded INTEGER DEFAULT 0, errors TEXT DEFAULT '[]'
);
CREATE UNIQUE INDEX single_active_scan ON scans((1)) WHERE status='running';
CREATE TABLE duplicate_review(
 left_id TEXT NOT NULL REFERENCES ventures(id) ON DELETE CASCADE, right_id TEXT NOT NULL REFERENCES ventures(id) ON DELETE CASCADE,
 decision TEXT NOT NULL DEFAULT 'pending', reason TEXT NOT NULL, updated_at TEXT NOT NULL, PRIMARY KEY(left_id,right_id)
);
CREATE TABLE intake(id INTEGER PRIMARY KEY, url TEXT UNIQUE NOT NULL, title TEXT NOT NULL, note TEXT NOT NULL, observed_at TEXT NOT NULL);
CREATE TABLE preferences(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL);
