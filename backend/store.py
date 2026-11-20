"""SQLite persistence, identity resolution and evidence search."""

from __future__ import annotations

import hashlib
import ipaddress
import json
import os
import re
import sqlite3
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from .scoring import assess, day, normalized

ROOT = Path(__file__).resolve().parents[1]
DEFAULTS = {
    "country": "DE",
    "keywords": "",
    "interval_hours": 24,
    "scheduled": False,
    "priority_threshold": 70,
}
SOURCES = [
    (
        "htgf",
        "HTGF portfolio",
        "Portfolio",
        "public_api",
        "available",
        "https://www.htgf.de/en/portfolio/",
        "Public portfolio reference index, including historical investments.",
        1,
        1,
    ),
    (
        "tum",
        "Technical University of Munich",
        "University",
        "public_page",
        "available",
        "https://www.tum.de/en/innovation/entrepreneurship/news-events/tum-ideaward",
        "TUM IDEAward finalists and their published commercial signals.",
        1,
        1,
    ),
    (
        "kit",
        "KIT-Gründerschmiede",
        "University",
        "public_page",
        "available",
        "https://www.kit-forge.de/en/magazine/",
        "KIT's public founder profiles in Karlsruhe.",
        1,
        1,
    ),
    (
        "companies_house",
        "Companies House",
        "Registry",
        "official_api",
        "credential_required",
        "https://developer.company-information.service.gov.uk/",
        "Set COMPANIES_HOUSE_API_KEY for bounded UK incorporation searches.",
        0,
        1,
    ),
    (
        "norway",
        "Brønnøysund Register Centre",
        "Registry",
        "official_api",
        "available",
        "https://data.brreg.no/enhetsregisteret/api/",
        "Date-limited register searches for Norwegian technology companies.",
        1,
        1,
    ),
    (
        "estonia",
        "Estonian e-Business Register",
        "Registry",
        "file_import",
        "manual_only",
        "https://avaandmed.ariregister.rik.ee/en",
        "Bounded local snapshot import. Registry dates determine incorporation.",
        0,
        0,
    ),
    (
        "german_register",
        "German commercial register",
        "Registry",
        "manual_only",
        "manual_only",
        "https://www.handelsregister.de/",
        "Analyst-verified notices with a court, register number and formation date.",
        0,
        0,
    ),
    (
        "github",
        "GitHub",
        "Developer",
        "enrichment",
        "on_demand",
        "https://docs.github.com/en/rest/search/search",
        "Repository research on explicit analyst request.",
        0,
        0,
    ),
    (
        "linkedin",
        "LinkedIn",
        "Community",
        "manual_only",
        "manual_only",
        "https://www.linkedin.com/",
        "Public links may be saved for analyst review.",
        0,
        0,
    ),
    (
        "instagram",
        "Instagram",
        "Community",
        "manual_only",
        "manual_only",
        "https://www.instagram.com/",
        "Public links may be saved for analyst review.",
        0,
        0,
    ),
    (
        "facebook",
        "Facebook",
        "Community",
        "manual_only",
        "manual_only",
        "https://www.facebook.com/",
        "Public links may be saved for analyst review.",
        0,
        0,
    ),
    (
        "huggingface",
        "Hugging Face",
        "Developer",
        "planned",
        "planned",
        "https://huggingface.co/docs/hub/",
        "Developer demo connector planned.",
        0,
        0,
    ),
    (
        "hn",
        "Hacker News",
        "Community",
        "planned",
        "planned",
        "https://news.ycombinator.com/",
        "Community connector planned.",
        0,
        0,
    ),
    (
        "exist",
        "EXIST",
        "Grant",
        "manual_only",
        "manual_only",
        "https://exist.de/en/",
        "German startup grants and transfer programmes. Manual verification.",
        0,
        0,
    ),
]
STAGES = {
    "UNKNOWN",
    "POTENTIAL_PRE_COMPANY",
    "EXISTING_EMERGING",
    "NEWLY_INCORPORATED",
    "RESEARCH_ONLY",
    "NOT_A_STARTUP",
}


def now():
    return (
        datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    )


def dump(obj):
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def digest(obj):
    return hashlib.sha256(dump(obj).encode()).hexdigest()


def dbpath():
    url = os.getenv("DATABASE_URL", "")
    if url and not url.startswith("sqlite:///"):
        raise ValueError("This edition supports SQLite DATABASE_URL values only.")
    return Path(
        os.getenv("FOUNDER_RADAR_DB")
        or (url[10:] if url else ROOT / "var" / "radar.sqlite3")
    )


@contextmanager
def connect():
    path = dbpath()
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path, timeout=20)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys=ON")
    try:
        with db:
            yield db
    finally:
        db.close()


def init():
    with connect() as db:
        db.execute("PRAGMA journal_mode=WAL")
        db.execute(
            "CREATE TABLE IF NOT EXISTS schema_version (version INTEGER PRIMARY KEY)"
        )
        if not db.execute("SELECT 1 FROM schema_version WHERE version=1").fetchone():
            sql = (ROOT / "backend/migrations/001_initial.sql").read_text()
            db.executescript(
                "BEGIN IMMEDIATE;"
                + sql
                + "INSERT INTO schema_version VALUES(1);COMMIT;"
            )
        try:
            db.execute(
                "CREATE VIRTUAL TABLE IF NOT EXISTS search_index USING fts5(id UNINDEXED, body,tokenize='unicode61 remove_diacritics 2')"
            )
        except sqlite3.OperationalError:
            db.execute(
                "CREATE TABLE IF NOT EXISTS search_index(id TEXT PRIMARY KEY,body TEXT)"
            )
        db.executemany(
            "INSERT INTO sources(id,name,kind,mode,status,url,notes,enabled,can_scan) VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET url=excluded.url,notes=excluded.notes",
            SOURCES,
        )

        campuses = ROOT / "registries/campus_directory.json"
        if campuses.is_file():
            for c in json.loads(campuses.read_text()):
                db.execute(
                    """INSERT OR IGNORE INTO sources(id,name,kind,mode,status,url,notes)
                           VALUES(?,?,?,'manual_only','manual_only',?,?)""",
                    (c["id"], c["name"], c["kind"], c["url"], c["notes"]),
                )


def web_url(value):
    if (
        not isinstance(value, str)
        or len(value) > 2048
        or any(ord(c) < 33 or c in '\\<>"' for c in value)
    ):
        raise ValueError("Enter a valid public website URL.")
    try:
        parts = urlsplit(value)
        port = parts.port
        host = parts.hostname or ""
    except ValueError as exc:
        raise ValueError("Invalid website address.") from exc
    if (
        parts.scheme not in ("http", "https")
        or parts.username
        or parts.password
        or port not in (None, 80, 443)
        or "." not in host
        or host.endswith((".local", ".localhost", ".internal", "."))
    ):
        raise ValueError("Only public HTTP or HTTPS addresses are supported.")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        if (
            not re.fullmatch(r"[a-zA-Z0-9.-]+", host)
            or re.fullmatch(r"[0-9.xa-f]+", host, flags=re.I)
            and any(c.isdigit() for c in host)
            and host.rsplit(".", 1)[-1].isdigit()
        ):
            raise ValueError("Invalid public hostname.")
    else:
        if not address.is_global:
            raise ValueError("Private addresses are unsupported.")
    return value


def prefs(db):
    return DEFAULTS | {
        r["key"]: json.loads(r["value"])
        for r in db.execute("SELECT * FROM preferences")
    }


def evidence_key(e):
    return digest(
        [
            e["source_id"],
            e["url"],
            e.get("signal_type") or "OTHER",
            normalized(e.get("quote") or e.get("claim")),
        ]
    )


def prepare(record):
    r = dict(record)
    if (
        not re.fullmatch(r"[\w.:-]{1,180}", str(r.get("id", "")))
        or not str(r.get("name", "")).strip()
        or r.get("kind") not in ("prospect", "portfolio")
    ):
        raise ValueError("A candidate requires a stable ID, name and collection.")
    if r.get("stage") not in STAGES:
        raise ValueError("Unknown venture stage.")
    if not r.get("evidence"):
        raise ValueError("An attributed source is required.")
    es = []
    for item in r.pop("evidence"):
        e = dict(item)
        web_url(e["url"])
        if (
            not e.get("source_id")
            or not e.get("source_name")
            or not (e.get("quote") or e.get("claim"))
        ):
            raise ValueError("Evidence requires a publisher and supporting text.")
        for key in ("first_observed_at", "retrieved_at"):
            if not day(e.get(key)):
                raise ValueError(f"Missing genuine source {key}.")
        for key in ("published_at", "event_date"):
            if e.get(key) and not day(e[key]):
                raise ValueError(f"Invalid {key} date.")
            e.setdefault(key, None)
        e.setdefault("signal_type", "OTHER")
        es.append(e)
    for key in ("team", "tags"):
        r.setdefault(key, [])
    for key in (
        "summary",
        "sector",
        "country",
        "city",
        "university",
        "website",
        "registered_at",
        "best_find",
    ):
        r.setdefault(key, None)
    r.setdefault("registration_status", "NOT_VERIFIED")
    r.setdefault("funding_status", "UNKNOWN")
    if r.get("website"):
        web_url(r["website"])
    if r["registration_status"] == "VERIFIED_REGISTERED" and not r.get("legal_entity"):
        r["registration_status"] = "PENDING_REVIEW"
    return r, es


def ingest(db, records, mode="recorded"):
    counts = {
        "created": 0,
        "updated": 0,
        "unchanged": 0,
        "documents": 0,
        "discarded": 0,
    }
    docs = set()
    for raw in records:
        r, es = prepare(raw)
        if db.execute(
            "SELECT 1 FROM metadata WHERE key=?", ("suppressed:" + r["id"],)
        ).fetchone():
            counts["discarded"] += 1
            continue
        candidate = r["id"]
        found = db.execute("SELECT * FROM ventures WHERE id=?", (candidate,)).fetchone()
        first = min(e["first_observed_at"] for e in es)
        last = max(e["retrieved_at"] for e in es)
        if found:
            # Replays can restore missing evidence, but do not revert fresher live metadata.
            prior = json.loads(found["payload"])
            if (
                mode in ("replay", "recorded") and found["last_verified_at"] > last
            ) or last < found["last_verified_at"]:
                r = prior
            else:
                r = {
                    **prior,
                    **{
                        k: v
                        for k, v in r.items()
                        if v is not None and v != [] and v != ""
                    },
                }
        if found and prior.get("legal_entity") and r.get("legal_entity"):
            old_legal = prior["legal_entity"]
            r["legal_entity"] = {
                **old_legal,
                **{k: v for k, v in r["legal_entity"].items() if v is not None},
            }
            if prior.get("registered_at") and not raw.get("registered_at"):
                r["registered_at"] = prior["registered_at"]
                r["stage"] = prior["stage"]

        def semantic(value):
            clocks = {
                "retrieved_at",
                "first_observed_at",
                "last_verified_at",
                "last_scanned_at",
                "capture_mode",
                "provenance",
            }
            if isinstance(value, dict):
                return {k: semantic(v) for k, v in value.items() if k not in clocks}
            if isinstance(value, list):
                return [semantic(v) for v in value]
            return value

        h = digest(semantic(r))
        db.execute(
            """INSERT INTO ventures VALUES(?,?,?,?,?,?,?,?,?,?,?,?)
         ON CONFLICT(id) DO UPDATE SET name=excluded.name,normalized_name=excluded.normalized_name,
         kind=excluded.kind,stage=excluded.stage,country=excluded.country,sector=excluded.sector,website=excluded.website,
         payload=excluded.payload,content_hash=excluded.content_hash,last_verified_at=max(ventures.last_verified_at,excluded.last_verified_at),
         first_observed_at=min(ventures.first_observed_at,excluded.first_observed_at)""",
            (
                candidate,
                r["name"],
                normalized(r["name"]),
                r["kind"],
                r["stage"],
                r["country"],
                r["sector"],
                r["website"],
                dump(r),
                h,
                first,
                last,
            ),
        )
        new_evidence = False
        for e in es:
            doc_id = digest([e["source_id"], e["url"]])
            docs.add(doc_id)
            doc_hash = digest([e.get("title"), e.get("published_at")])
            db.execute(
                """INSERT INTO documents VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET
                last_changed_at=CASE WHEN excluded.content_hash<>documents.content_hash AND excluded.retrieved_at>=documents.retrieved_at THEN excluded.retrieved_at ELSE documents.last_changed_at END,
                content_hash=CASE WHEN excluded.retrieved_at>=documents.retrieved_at THEN excluded.content_hash ELSE documents.content_hash END,
                title=CASE WHEN excluded.retrieved_at>=documents.retrieved_at THEN excluded.title ELSE documents.title END,
                published_at=coalesce(documents.published_at,excluded.published_at),retrieved_at=max(documents.retrieved_at,excluded.retrieved_at),
                first_observed_at=min(documents.first_observed_at,excluded.first_observed_at)""",
                (
                    doc_id,
                    e["source_id"],
                    e["url"],
                    e.get("title") or r["name"],
                    doc_hash,
                    e["published_at"],
                    e["first_observed_at"],
                    e["retrieved_at"],
                    e["retrieved_at"],
                    mode,
                ),
            )
            identity = evidence_key(e)
            eid = digest([candidate, identity])[:24]
            e["id"] = eid
            prev = db.execute(
                "SELECT evidence_json FROM evidence WHERE id=?", (eid,)
            ).fetchone()
            if prev:
                previous = json.loads(prev[0])
                original = min(e["first_observed_at"], previous["first_observed_at"])
                if previous["retrieved_at"] > e["retrieved_at"]:
                    e = previous
                e["first_observed_at"] = original
            else:
                new_evidence = True
            db.execute(
                """INSERT INTO evidence(id,candidate_id,document_id,source_id,evidence_json,identity) VALUES(?,?,?,?,?,?)
                         ON CONFLICT(id) DO UPDATE SET evidence_json=excluded.evidence_json""",
                (eid, candidate, doc_id, e["source_id"], dump(e), identity),
            )
            db.execute(
                """INSERT INTO signals VALUES(?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET event_date=excluded.event_date,
                          first_observed_at=min(signals.first_observed_at,excluded.first_observed_at)""",
                (
                    eid,
                    candidate,
                    eid,
                    e.get("signal_type") or "OTHER",
                    e.get("event_date"),
                    e["first_observed_at"],
                ),
            )
        legal = r.get("legal_entity")
        if legal and legal.get("registration_number"):
            number = legal["registration_number"]
            registry = (
                legal.get("registry_name")
                or legal.get("source_key")
                or es[0]["source_id"]
            )
            legalid = digest([r["country"], registry, number])
            db.execute(
                "INSERT INTO legal_entities VALUES(?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload",
                (
                    legalid,
                    r["country"],
                    registry,
                    number,
                    r.get("registered_at"),
                    legal.get("official_url") or es[0]["url"],
                    dump(legal),
                ),
            )
            db.execute(
                "INSERT OR IGNORE INTO legal_links VALUES(?,?)", (candidate, legalid)
            )
        status = (
            "created"
            if not found
            else "updated"
            if new_evidence or found["content_hash"] != h
            else "unchanged"
        )
        counts[status] += 1
        if status != "unchanged":
            detail = (
                "First recorded evidence"
                if not found
                else "Additional evidence or source details"
            )
            db.execute(
                "INSERT INTO changes(candidate_id,kind,observed_at,mode,detail) VALUES(?,?,?,?,?)",
                (candidate, status, now(), mode, detail),
            )
            full = load(db, [candidate])[0]
            body = normalized(
                " ".join(
                    str(v or "")
                    for v in [
                        r["name"],
                        r["summary"],
                        r["sector"],
                        r["country"],
                        r["city"],
                        r["university"],
                        *r["tags"],
                        *(p.get("name", "") for p in r["team"]),
                        *(
                            e.get(k, "")
                            for e in full["evidence"]
                            for k in (
                                "quote",
                                "claim",
                                "source_name",
                                "signal_type",
                                "title",
                            )
                        ),
                    ]
                )
            )
            db.execute("DELETE FROM search_index WHERE id=?", (candidate,))
            db.execute("INSERT INTO search_index VALUES(?,?)", (candidate, body))
            if r["website"] and r["kind"] == "prospect":
                same = db.execute(
                    "SELECT id FROM ventures WHERE website=? AND id<>? AND kind=? AND country IS ?",
                    (r["website"], candidate, "prospect", r["country"]),
                )
                for other in same:
                    pair = sorted([candidate, other[0]])
                    db.execute(
                        "INSERT OR IGNORE INTO duplicate_review VALUES(?,?,'pending',?,?)",
                        (
                            *pair,
                            "Shared official project URL and country. Verify identity.",
                            now(),
                        ),
                    )
    counts["documents"] = len(docs)
    return counts


def load(db, ids=None):
    where = (
        ""
        if ids is None
        else f" WHERE v.id IN ({','.join('?' for _ in ids) or 'NULL'})"
    )
    values = tuple(ids or ())
    base = db.execute(
        "SELECT v.*,s.watched,s.note,s.decision FROM ventures v LEFT JOIN review_state s ON v.id=s.candidate_id"
        + where,
        values,
    )
    rows = {
        v["id"]: json.loads(v["payload"])
        | {
            "first_observed_at": v["first_observed_at"],
            "last_verified_at": v["last_verified_at"],
            "watched": bool(v["watched"]),
            "note": v["note"] or "",
            "review_status": v["decision"] or "unreviewed",
            "evidence": [],
        }
        for v in base
    }
    query = "SELECT candidate_id,evidence_json FROM evidence WHERE active=1"
    if ids is not None:
        query += " AND candidate_id IN (" + (",".join("?" for _ in ids) or "NULL") + ")"
    for e in db.execute(query, values):
        rows[e[0]]["evidence"].append(json.loads(e[1]))
    return [assess(r) for r in rows.values()]


def integer(value, default, lo, hi):
    if value in ("", None):
        return default
    try:
        n = int(value)
    except (ValueError, TypeError):
        raise ValueError("Expected a whole number.") from None
    if n < lo or n > hi:
        raise ValueError(f"Value must be between {lo} and {hi}.")
    return n


def search(db, p, export=False):
    kind = p.get("kind", "prospect") or "prospect"
    if kind not in {"prospect", "portfolio", "all"}:
        raise ValueError("Unknown collection.")
    terms = re.findall(r"[^\W_]+", normalized(p.get("q", ""))[:260])
    ids = None
    if terms:
        try:
            fts = " AND ".join('"' + t + '"*' for t in terms)
            ids = [
                r[0]
                for r in db.execute(
                    "SELECT id FROM search_index WHERE search_index MATCH ?", (fts,)
                )
            ]
        except sqlite3.OperationalError:
            ids = [
                r[0]
                for r in db.execute(
                    "SELECT id FROM search_index WHERE "
                    + " AND ".join("instr(body,?)>0" for _ in terms),
                    terms,
                )
            ]
    items = load(db, ids)
    all_items = [r for r in items if kind == "all" or r["kind"] == kind]
    facets = {
        "countries": sorted({r["country"] for r in all_items if r["country"]}),
        "sectors": sorted({r["sector"] for r in all_items if r["sector"]}),
        "sources": sorted({e["source_id"] for r in all_items for e in r["evidence"]}),
    }
    quality = integer(p.get("min_quality"), 0, 0, 100)
    confidence = integer(p.get("min_confidence"), 0, 0, 100)
    days = integer(p.get("days"), 90, 1, 3650)
    today = datetime.now(timezone.utc).date()
    filtered = []
    for r in all_items:
        if any(
            p.get(k) and p[k] != "all" and r.get(k) != p[k]
            for k in (
                "country",
                "sector",
                "funding_status",
                "registration_status",
                "review_status",
            )
        ):
            continue
        if p.get("university") and normalized(p["university"]) not in normalized(
            r["university"]
        ):
            continue
        if p.get("source") and not any(
            e["source_id"] == p["source"] for e in r["evidence"]
        ):
            continue
        if p.get("watch") in ("true", "1") and not r["watched"]:
            continue
        if r["scores"]["quality"] < quality or r["scores"]["confidence"] < confidence:
            continue
        if any(
            p.get(k)
            and (not r["first_observed_at"] or op(r["first_observed_at"][:10], p[k]))
            for k, op in [("observed_from", str.__lt__), ("observed_to", str.__gt__)]
        ):
            continue
        if p.get("published_from") or p.get("published_to"):
            if not any(
                e.get("published_at")
                and p.get("published_from", "")
                <= e["published_at"][:10]
                <= p.get("published_to", "9999")
                for e in r["evidence"]
            ):
                continue
        if (
            r["stage"] == "NEWLY_INCORPORATED"
            and (p.get("stage") or p.get("state")) == "NEWLY_INCORPORATED"
            and (today - day(r["registered_at"])).days >= days
        ):
            continue
        filtered.append(r)
    stage_counts = dict(Counter(r["stage"] for r in filtered))
    stage_counts["ALL"] = len(filtered)
    stage = p.get("stage") or p.get("state")
    if stage and stage.upper() != "ALL":
        filtered = [r for r in filtered if r["stage"] == stage]
    sort = p.get("sort", "priority")
    filtered.sort(key=lambda r: r["name"].casefold())
    if sort in ("priority", "quality", "confidence"):
        filtered.sort(key=lambda r: r["scores"][sort], reverse=True)
    elif sort == "recent":
        filtered.sort(key=lambda r: r["last_signal_at"] or "", reverse=True)
    limit = integer(p.get("limit"), 20, 1, 100)
    page = integer(p.get("page"), 1, 1, 100000)
    return {
        "items": filtered if export else filtered[(page - 1) * limit : page * limit],
        "total": len(filtered),
        "page": page,
        "limit": limit,
        "facets": facets,
        "stage_counts": stage_counts,
    }


def source_list(db):
    result = []
    for row in db.execute("SELECT * FROM sources ORDER BY rowid"):
        r = dict(row)
        r["enabled"] = bool(r["enabled"])
        r["can_scan"] = bool(r["can_scan"])
        if r["id"] == "companies_house" and os.getenv("COMPANIES_HOUSE_API_KEY"):
            r["status"] = "key_configured"
        if r["last_error"]:
            r["status"] = (
                "failed" if r["status"] != "credential_required" else r["status"]
            )
        if r["last_success_at"] and not r["last_error"]:
            r["status"] = "live" if r["can_scan"] else r["status"]
        result.append(r)
    return result


def set_review(db, candidate, body):
    if not db.execute("SELECT 1 FROM ventures WHERE id=?", (candidate,)).fetchone():
        raise KeyError(candidate)
    db.execute(
        "INSERT OR IGNORE INTO review_state(candidate_id) VALUES(?)", (candidate,)
    )
    if "watched" in body:
        if not isinstance(body["watched"], bool):
            raise ValueError("watched must be true or false.")
        db.execute(
            "UPDATE review_state SET watched=? WHERE candidate_id=?",
            (body["watched"], candidate),
        )
    if "note" in body:
        if not isinstance(body["note"], str) or len(body["note"]) > 5000:
            raise ValueError("Notes must be at most 5000 characters.")
        db.execute(
            "UPDATE review_state SET note=? WHERE candidate_id=?",
            (body["note"], candidate),
        )
    if "decision" in body:
        if body["decision"] not in (
            "watch",
            "accept",
            "reject",
            "review",
            "unreviewed",
        ):
            raise ValueError("Unknown review decision.")
        db.execute(
            "UPDATE review_state SET decision=? WHERE candidate_id=?",
            (body["decision"], candidate),
        )
        if body["decision"] == "watch":
            db.execute(
                "UPDATE review_state SET watched=1 WHERE candidate_id=?", (candidate,)
            )
    db.execute(
        "INSERT INTO reviews(candidate_id,decision,note,at) VALUES(?,?,?,?)",
        (
            candidate,
            body.get(
                "decision",
                "watch"
                if body.get("watched")
                else "unwatch"
                if "watched" in body
                else "note",
            ),
            body.get("note"),
            now(),
        ),
    )
    return load(db, [candidate])[0]
