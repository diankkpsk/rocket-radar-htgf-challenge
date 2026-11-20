from __future__ import annotations

import json
import logging
import threading
import uuid

from . import store as s


def recordings():
    path = s.ROOT / "data/records.json"
    records = json.loads(path.read_text()) if path.exists() else []
    from registries import recorded_registrations, to_record

    return records + [to_record(r) for r in recorded_registrations()]


def source_of(record):
    return record["evidence"][0]["source_id"]


def seed():
    records = recordings()
    key = s.digest(records)
    with s.connect() as db:
        old = db.execute("SELECT value FROM metadata WHERE key='snapshot'").fetchone()
        if old and old[0] == key:
            return
        for source in sorted({source_of(r) for r in records}):
            batch = [r for r in records if source_of(r) == source]
            counts = s.ingest(db, batch, "recorded")
            stamp = s.now()
            db.execute(
                """INSERT INTO scans(id,source_id,mode,status,started_at,completed_at,created,updated,unchanged,documents,discarded)
             VALUES(?,?,'replay','success',?,?,?,?,?,?,?)""",
                (
                    uuid.uuid4().hex,
                    source,
                    stamp,
                    stamp,
                    counts["created"],
                    counts["updated"],
                    counts["unchanged"],
                    counts["documents"],
                    counts["discarded"],
                ),
            )
        db.execute("INSERT OR REPLACE INTO metadata VALUES('snapshot',?)", (key,))


def fix_interrupted():
    with s.connect() as db:
        db.execute(
            "UPDATE scans SET status='failed',completed_at=?,errors=? WHERE status='running'",
            (
                s.now(),
                s.dump(["The previous server stopped before completing this scan."]),
            ),
        )


def scan_dict(row):
    data = dict(row)
    data["errors"] = json.loads(data["errors"])
    return data


def reserve(source_id, mode, days=30):
    if mode not in ("live", "replay"):
        raise ValueError("Choose live or replay.")
    with s.connect() as db:
        source = db.execute("SELECT * FROM sources WHERE id=?", (source_id,)).fetchone()
        if not source:
            raise ValueError("Select a registered source.")
        if mode == "live" and not source["can_scan"]:
            raise ValueError("This source supports manual verification only.")
        if mode == "live" and not source["enabled"] and source_id != "companies_house":
            raise ValueError("Enable this source before scanning.")
        job = uuid.uuid4().hex
        try:
            db.execute(
                "INSERT INTO scans(id,source_id,mode,status,started_at) VALUES(?,?,?,'running',?)",
                (job, source_id, mode, s.now()),
            )
        except s.sqlite3.IntegrityError:
            raise RuntimeError(
                "A scan is already running. Check scan history."
            ) from None
        data = scan_dict(
            db.execute("SELECT * FROM scans WHERE id=?", (job,)).fetchone()
        )
    return data


def run(job, days=30):
    source = job["source_id"]
    mode = job["mode"]
    records = []
    errors = []
    discarded = 0
    status = "success"
    try:
        if mode == "replay":
            records = [r for r in recordings() if source_of(r) == source]
            if not records:
                raise ValueError("No recorded evidence bundle for this source.")
        elif source in ("companies_house", "norway"):
            from registries import companies_house, norway, to_record

            batch = (companies_house if source == "companies_house" else norway)(days)
            records = [to_record(r) for r in batch["records"]]
            status = batch["status"]
            errors = batch["errors"]
            discarded = (
                sum(batch["discarded"].values())
                if isinstance(batch["discarded"], dict)
                else batch["discarded"]
            )
        elif source in ("tum", "kit", "htgf"):
            from collectors import collect

            records = collect(source)
            if not records:
                raise ValueError("The source returned no readable entries.")
        else:
            raise ValueError("No automatic collection adapter for this source.")
        with s.connect() as db:
            counts = s.ingest(db, records, mode)
            finish(db, job, counts, status, errors, discarded)
    except Exception as exc:
        logging.getLogger(__name__).warning(
            "Scan %s failed (%s).", job["id"], type(exc).__name__
        )
        # No raw HTTP headers, auth or exception traces enter the database.
        message = str(exc)
        for secret in ("COMPANIES_HOUSE_API_KEY", "GITHUB_TOKEN"):
            value = s.os.getenv(secret)
            if value:
                message = message.replace(value, "[redacted]")
        with s.connect() as db:
            finish(db, job, {}, "failed", [f"{type(exc).__name__}: {message[:360]}"], 0)


def finish(db, job, counts, status, errors, discarded):
    stamp = s.now()
    db.execute(
        "UPDATE scans SET status=?,completed_at=?,created=?,updated=?,unchanged=?,documents=?,discarded=?,errors=? WHERE id=?",
        (
            status,
            stamp,
            *(
                counts.get(k, 0)
                for k in ("created", "updated", "unchanged", "documents")
            ),
            discarded,
            s.dump(errors),
            job["id"],
        ),
    )
    if job["mode"] == "live":
        db.execute(
            "UPDATE sources SET last_attempt_at=?,last_success_at=CASE WHEN ? THEN ? ELSE last_success_at END,last_error=? WHERE id=?",
            (
                stamp,
                status == "success",
                stamp,
                " · ".join(errors)[:650] or None,
                job["source_id"],
            ),
        )


def start(source_id, mode, days=30):
    job = reserve(source_id, mode, days)
    threading.Thread(
        target=run, args=(job, days), name="scan-" + job["id"][:8], daemon=True
    ).start()
    return job
