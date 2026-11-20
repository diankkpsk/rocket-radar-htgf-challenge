"""Loopback-only, same-origin HTTP API for the evidence workspace."""

from __future__ import annotations

import os
from collections import Counter
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from typing import Literal

from alembic import command
from alembic.config import Config
from fastapi import Body, FastAPI, Query, Request
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field
from registries import coverage, german_notice, repository_search, to_record

from . import export, jobs, store as s


def initialize():
    command.upgrade(Config(str(s.ROOT / "alembic.ini")), "head")
    s.init()
    jobs.seed()


@asynccontextmanager
async def lifespan(app):
    initialize()
    jobs.fix_interrupted()
    yield


app = FastAPI(
    title="FounderRadar",
    version="1.0.0",
    description="Evidence-led venture discovery for a single local analyst.",
    lifespan=lifespan,
)
api = "/api/v1"


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ScanRequest(Model):
    source_id: str = Field(min_length=1, max_length=100)
    mode: Literal["live", "replay"] = "live"
    days: Literal[7, 30, 90] = 30


class Watch(Model):
    watched: bool


class Review(Model):
    decision: Literal["accept", "reject", "review", "watch", "unreviewed"] | None = None
    note: str | None = Field(None, max_length=5000)


class Intake(Model):
    url: str = Field(max_length=2048)
    title: str = Field("", max_length=200)
    note: str = Field("", max_length=3000)


class NewSource(Model):
    name: str = Field(min_length=1, max_length=140)
    url: str = Field(max_length=2048)
    notes: str = Field("", max_length=1500)


class SourceSwitch(Model):
    enabled: bool


class Settings(Model):
    country: str | None = Field(None, max_length=3)
    keywords: str | None = Field(None, max_length=500)
    interval_hours: int | None = Field(None, ge=1, le=720)
    scheduled: bool | None = None
    priority_threshold: int | None = Field(None, ge=0, le=100)


class PairDecision(Model):
    left_id: str
    right_id: str
    decision: Literal["related", "distinct", "pending"]


@app.middleware("http")
async def local_access(req: Request, call_next):
    host = req.url.hostname
    if host not in ("127.0.0.1", "localhost", "::1", "testserver"):
        return JSONResponse(
            {"error": "Use the local workspace address."}, status_code=403
        )
    if req.method not in ("GET", "HEAD", "OPTIONS"):
        origin = req.headers.get("origin")
        if req.headers.get("sec-fetch-site") == "cross-site" or (
            origin and origin != str(req.base_url).rstrip("/")
        ):
            return JSONResponse(
                {"error": "Cross-origin changes are disabled."}, status_code=403
            )
        if req.headers.get("content-type", "").split(";")[0] != "application/json":
            return JSONResponse({"error": "Send application/json."}, status_code=415)
        size = req.headers.get("content-length", "")
        if size and (not size.isdigit() or int(size) > 32768):
            return JSONResponse(
                {"error": "Request exceeds size limit."}, status_code=413
            )
        received = bytearray()
        async for chunk in req.stream():
            received.extend(chunk)
            if len(received) > 32768:
                return JSONResponse(
                    {"error": "Request exceeds size limit."}, status_code=413
                )
        # Starlette replays the buffered body to downstream schema validation.
        req._body = bytes(received)
    resp = await call_next(req)
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["Referrer-Policy"] = "no-referrer"
    resp.headers["X-Frame-Options"] = "DENY"
    if not req.url.path.startswith(("/docs", "/redoc")):
        resp.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; font-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; object-src 'none'; base-uri 'none'; form-action 'self'"
        )
    if req.url.path.startswith(api):
        resp.headers["Cache-Control"] = "no-store"
    return resp


@app.exception_handler(ValueError)
async def validation(req, exc):
    return JSONResponse(
        {"error": str(exc)[:350], "detail": str(exc)[:350]}, status_code=422
    )


@app.exception_handler(KeyError)
async def missing(req, exc):
    return JSONResponse(
        {"error": "Record not found.", "detail": "Record not found."}, status_code=404
    )


@app.exception_handler(RuntimeError)
async def conflict(req, exc):
    return JSONResponse(
        {"error": str(exc)[:350], "detail": str(exc)[:350]}, status_code=409
    )


@app.get("/health")
def health():
    with s.connect() as db:
        db.execute("SELECT 1 FROM schema_version").fetchone()
    return {"status": "ok", "database": "ready", "version": app.version}


@app.get(api + "/stats")
def stats():
    with s.connect() as db:
        rows = s.load(db)
        prospects = [r for r in rows if r["kind"] == "prospect"]
        stages = dict(Counter(r["stage"] for r in prospects))
        best = next((r for r in prospects if r.get("best_find")), None)
        settings = s.prefs(db)
        sources = db.execute(
            "SELECT count(DISTINCT source_id) FROM documents"
        ).fetchone()[0]
        mode = db.execute(
            "SELECT DISTINCT mode FROM scans WHERE status='success'"
        ).fetchall()
        modes = {m[0] for m in mode}
        week = (datetime.now(timezone.utc) - timedelta(days=7)).date().isoformat()
        return {
            "prospects": len(prospects),
            "portfolio": len(rows) - len(prospects),
            "watchlist": sum(r["watched"] for r in rows),
            "evidence": sum(r["evidence_count"] for r in rows),
            "sources": sources,
            "as_of": max((r["last_verified_at"] for r in rows), default=None),
            "stage_counts": stages,
            "best_find": best,
            "mode": "mixed"
            if modes == {"replay", "live"}
            else "live"
            if modes == {"live"}
            else "recorded",
            "new_this_week": sum(
                r["first_observed_at"][:10] >= week for r in prospects
            ),
            "high_priority": sum(
                r["scores"]["quality"] >= settings["priority_threshold"]
                and r["scores"]["confidence"] >= 55
                for r in prospects
            ),
            "errors": db.execute(
                "SELECT count(*) FROM sources WHERE last_error IS NOT NULL"
            ).fetchone()[0],
        }


@app.get(api + "/leads")
@app.get(api + "/search")
def find(request: Request):
    if len(request.url.query) > 3500:
        raise ValueError("Query too long.")
    with s.connect() as db:
        return s.search(db, dict(request.query_params))


def read_lead(db, id):
    found = s.load(db, [id])
    if not found:
        raise KeyError(id)
    return found[0]


@app.get(api + "/leads/{id}")
def lead(id: str):
    with s.connect() as db:
        return read_lead(db, id)


@app.get(api + "/leads/{id}/timeline")
def timeline(id: str):
    with s.connect() as db:
        record = read_lead(db, id)
        events = [
            {
                "kind": "evidence",
                "date": e["event_date"] or e["published_at"],
                "observed": e["first_observed_at"],
                "evidence": e,
            }
            for e in record["evidence"]
        ]
        events.extend(
            {
                "kind": "observation",
                "date": r["observed_at"],
                "detail": r["detail"],
                "mode": r["mode"],
            }
            for r in db.execute("SELECT * FROM changes WHERE candidate_id=?", (id,))
        )
        return {
            "items": sorted(
                events,
                key=lambda e: (
                    not bool(e.get("date")),
                    e.get("date") or e.get("observed") or "",
                ),
            )
        }


@app.post(api + "/leads/{id}/watch")
def watch(id: str, body: Watch):
    with s.connect() as db:
        return s.set_review(db, id, body.model_dump())


@app.post(api + "/leads/{id}/review")
def review(id: str, body: Review):
    with s.connect() as db:
        return s.set_review(db, id, body.model_dump(exclude_none=True))


@app.get(api + "/sources")
def sources():
    with s.connect() as db:
        return {"items": s.source_list(db)}


@app.post(api + "/sources", status_code=201)
def add_source(body: NewSource):
    url = s.web_url(body.url)
    key = "manual-" + s.digest(url)[:16]
    with s.connect() as db:
        db.execute(
            """INSERT INTO sources(id,name,kind,mode,status,url,notes) VALUES(?,?,'Other','manual_only','manual_only',?,?)
                      ON CONFLICT(id) DO UPDATE SET name=excluded.name, notes=excluded.notes""",
            (key, body.name, url, body.notes),
        )
        return dict(db.execute("SELECT * FROM sources WHERE id=?", (key,)).fetchone())


@app.post(api + "/sources/{id}")
def source_update(id: str, body: SourceSwitch):
    with s.connect() as db:
        if not db.execute(
            "UPDATE sources SET enabled=? WHERE id=? AND can_scan=1", (body.enabled, id)
        ).rowcount:
            raise ValueError("Only an implemented source connector can be enabled.")
        return {"id": id, "enabled": body.enabled}


@app.get(api + "/coverage")
def registry_coverage(q: str = ""):
    return {"items": coverage(q)}


@app.get(api + "/scans")
def scans():
    with s.connect() as db:
        return {
            "items": [
                jobs.scan_dict(r)
                for r in db.execute(
                    "SELECT * FROM scans ORDER BY started_at DESC,rowid DESC LIMIT 100"
                )
            ]
        }


@app.post(api + "/scans", status_code=202)
def scan(body: ScanRequest):
    return jobs.start(body.source_id, body.mode, body.days)


@app.get(api + "/scans/{id}")
def scan_detail(id: str):
    with s.connect() as db:
        r = db.execute("SELECT * FROM scans WHERE id=?", (id,)).fetchone()
        if not r:
            raise KeyError(id)
        return jobs.scan_dict(r)


@app.get(api + "/changes")
def changes():
    with s.connect() as db:
        return {
            "items": [
                dict(r)
                for r in db.execute(
                    "SELECT c.*,v.name FROM changes c JOIN ventures v ON v.id=c.candidate_id ORDER BY c.id DESC LIMIT 100"
                )
            ]
        }


@app.get(api + "/settings")
def settings():
    with s.connect() as db:
        return s.prefs(db) | {
            "credentials": {
                "companies_house": bool(os.getenv("COMPANIES_HOUSE_API_KEY")),
                "github": bool(os.getenv("GITHUB_TOKEN")),
                "brave": bool(os.getenv("BRAVE_SEARCH_API_KEY")),
            },
            "scheduler_requires_process": True,
        }


@app.post(api + "/settings")
def update_settings(body: Settings):
    fields = body.model_dump(exclude_none=True)
    if (
        "country" in fields
        and fields["country"] not in ("", "ALL", "all")
        and fields["country"] not in {r["country_code"] for r in coverage()}
    ):
        raise ValueError("Unknown focus country.")
    with s.connect() as db:
        db.executemany(
            "INSERT OR REPLACE INTO preferences VALUES(?,?)",
            [(k, s.dump(v)) for k, v in fields.items()],
        )
        return s.prefs(db)


@app.post(api + "/import-url", status_code=201)
def intake(body: Intake):
    url = s.web_url(body.url)
    with s.connect() as db:
        db.execute(
            "INSERT INTO intake(url,title,note,observed_at) VALUES(?,?,?,?) ON CONFLICT(url) DO UPDATE SET title=excluded.title,note=excluded.note",
            (url, body.title, body.note, s.now()),
        )
        return dict(
            db.execute("SELECT * FROM intake WHERE url=?", (url,)).fetchone()
        ) | {"mode": "manual_only"}


@app.get(api + "/imports")
def manual_inbox():
    with s.connect() as db:
        return {
            "items": [
                dict(r)
                for r in db.execute("SELECT * FROM intake ORDER BY id DESC LIMIT 100")
            ]
        }


@app.get(api + "/duplicates")
def duplicate_queue():
    with s.connect() as db:
        items = []
        for row in db.execute(
            "SELECT * FROM duplicate_review ORDER BY updated_at DESC LIMIT 60"
        ):
            item = dict(row)
            item["left"] = read_lead(db, item["left_id"])
            item["right"] = read_lead(db, item["right_id"])
            items.append(item)
        return {"items": items}


@app.post(api + "/duplicates")
def duplicate_decision(body: PairDecision):
    with s.connect() as db:
        if not db.execute(
            "UPDATE duplicate_review SET decision=?,updated_at=? WHERE left_id=? AND right_id=?",
            (body.decision, s.now(), body.left_id, body.right_id),
        ).rowcount:
            raise KeyError("pair")
    return body


@app.post(api + "/registry-notice")
def manual_notice(body: dict = Body(...)):
    record = to_record(german_notice(body))
    with s.connect() as db:
        s.ingest(db, [record], "manual")
        return read_lead(db, record["id"])


class WebQuery(Model):
    query: str = Field(min_length=1, max_length=250)
    country: str = Field("DE", min_length=2, max_length=3)


@app.get(api + "/discovery/plan")
def discovery_plan(country: str = "DE", technology: str = "", limit: int = 14):
    from .discovery import plan

    return plan(country, technology, limit)


@app.post(api + "/discovery/web")
def outbound_search(body: WebQuery):
    from .discovery import web_search

    return web_search(body.query, body.country)


@app.get(api + "/evaluation")
def evaluation():
    from .evaluation import report

    with s.connect() as db:
        return report(db)


@app.get(api + "/developer/github")
def github(q: str = Query(min_length=4, max_length=120)):
    return repository_search(q, page_size=6)


@app.get(api + "/exports/leads.csv")
def csv_export(request: Request):
    with s.connect() as db:
        content = export.table(
            s.search(db, dict(request.query_params), export=True)["items"]
        )
    return Response(
        content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="founderradar.csv"'},
    )


@app.get(api + "/exports/leads/{id}.md")
def memo_export(id: str):
    with s.connect() as db:
        content = export.memo(read_lead(db, id))
    return Response(
        content,
        media_type="text/markdown; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{id}.md"'},
    )


@app.get("/", include_in_schema=False)
def workspace():
    return FileResponse(
        s.ROOT / "frontend/index.html", headers={"Cache-Control": "no-cache"}
    )


app.mount("/frontend", StaticFiles(directory=s.ROOT / "frontend"), name="frontend")
