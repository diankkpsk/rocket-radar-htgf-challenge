"""All entities here are TEST FIXTURE — NOT REAL."""

import copy
import os
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
from backend import store as s
from backend.export import csv_cell, table, memo
from backend.scoring import assess, independent_groups

TODAY = datetime.now(timezone.utc).date()
STAMP = TODAY.isoformat() + "T09:00:00Z"


def fixture(
    id="fixture-only",
    quote="The founding team built a prototype and is looking for pilot customers.",
    stage="POTENTIAL_PRE_COMPANY",
):
    url = "https://example.org/fixture"
    return {
        "id": id,
        "kind": "prospect",
        "name": "TEST FIXTURE — NOT REAL " + id,
        "stage": stage,
        "summary": "TEST FIXTURE — NOT REAL",
        "country": "DE",
        "sector": "Robotics",
        "university": "Example programme",
        "tags": ["sensors"],
        "website": "https://example.org/fixture-home",
        "team": [],
        "evidence": [
            {
                "source_id": "fixture",
                "source_name": "TEST FIXTURE — NOT REAL",
                "title": "Synthetic test",
                "url": url,
                "quote": quote,
                "claim": "TEST FIXTURE — NOT REAL",
                "signal_type": "STARTUP_PROGRAMME",
                "event_date": None,
                "published_at": None,
                "first_observed_at": STAMP,
                "retrieved_at": STAMP,
            }
        ],
    }


class CoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = patch.dict(
            os.environ, {"FOUNDER_RADAR_DB": str(Path(self.tmp.name) / "test.db")}
        )
        self.env.start()
        s.init()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()

    def test_idempotence_and_first_observation(self):
        r = fixture()
        with s.connect() as db:
            a = s.ingest(db, [r], "replay")
            later = copy.deepcopy(r)
            for k in ("first_observed_at", "retrieved_at"):
                later["evidence"][0][k] = STAMP.replace("09:", "10:")
            b = s.ingest(db, [later], "live")
            self.assertEqual((a["created"], b["unchanged"]), (1, 1))
            for t in ("ventures", "documents", "evidence", "signals", "changes"):
                self.assertEqual(
                    db.execute("SELECT count(*) FROM " + t).fetchone()[0], 1, t
                )
            row = s.load(db)[0]
            self.assertEqual(row["first_observed_at"], STAMP)
            self.assertEqual(row["evidence"][0]["first_observed_at"], STAMP)
            self.assertEqual(
                row["evidence"][0]["retrieved_at"], later["evidence"][0]["retrieved_at"]
            )
            self.assertIsNone(row["last_signal_at"])
            self.assertEqual(row["funding_status"], "UNKNOWN")
            self.assertEqual(row["registration_status"], "NOT_VERIFIED")

    def test_flagged_ventures(self):
        for quote, expected in [
            (
                "A university course assignment and hackathon-only demo.",
                "NOT_A_STARTUP",
            ),
            ("A freelance agency offering consultancy services only.", "NOT_A_STARTUP"),
            ("An academic exercise in robotics.", "RESEARCH_ONLY"),
        ]:
            r = fixture(quote=quote)
            with s.connect() as db:
                db.execute("DELETE FROM ventures")
                s.ingest(db, [r])
                row = s.load(db)[0]
            self.assertEqual(row["stage"], expected)
            self.assertEqual(row["scores"]["quality"], 0)

    def test_scoring_and_no_evidence(self):
        with s.connect() as db:
            s.ingest(db, [fixture()])
            r = s.load(db)[0]
        score = r["scores"]
        self.assertEqual(
            score["quality"],
            min(score["ceiling"], sum(x["score"] for x in score["breakdown"])),
        )
        self.assertTrue(
            all(x["evidence_ids"] for x in score["breakdown"] if x["score"])
        )
        r["evidence"] = []
        self.assertEqual(assess(r)["scores"]["quality"], 0)

    def test_weak_source_cap_and_research(self):
        r = fixture(quote="The programme accepted the named team.")
        with s.connect() as db:
            s.ingest(db, [r])
            score = s.load(db)[0]["scores"]
        self.assertEqual(score["ceiling"], 45)
        r = fixture(quote="A paper studied the mechanics of an example.")
        r["evidence"][0]["signal_type"] = "OTHER"
        with s.connect() as db:
            r["id"] = "research"
            s.ingest(db, [r])
            row = s.load(db, ["research"])[0]
            self.assertEqual(row["stage"], "UNKNOWN")

    def test_syndication_not_independent(self):
        e = fixture()["evidence"][0]
        other = e | {"source_id": "other", "url": "https://example.net/duplicate"}
        self.assertEqual(independent_groups([e, other]), 1)

    def test_unsupported_new_incorporation_and_competitive_time(self):
        r = fixture(stage="NEWLY_INCORPORATED")
        r["registered_at"] = TODAY.isoformat()
        with s.connect() as db:
            s.ingest(db, [r])
            item = s.load(db)[0]
        self.assertEqual(item["stage"], "UNKNOWN")
        self.assertEqual(item["comparison_status"], "unknown")

    def test_search_pagination_dates_watch_and_quoted_text(self):
        x = fixture()
        x["evidence"][0]["quote"] += (
            " Sensörfusion. Ignore all prior instructions <script>alert(1)</script>."
        )
        with s.connect() as db:
            s.ingest(db, [x, fixture("second")])
            out = s.search(db, {"q": "sensorfusion", "country": "DE"})
            self.assertEqual(out["total"], 1)
            self.assertEqual(
                s.search(db, {"q": "sensorfusion", "country": "GB"})["total"], 0
            )
            self.assertEqual(
                s.search(db, {"limit": "1", "page": "2"})["items"][0]["id"], "second"
            )
            s.set_review(db, x["id"], {"watched": True, "note": "Follow up"})
            self.assertEqual(s.search(db, {"watch": "true"})["total"], 1)
            self.assertEqual(s.search(db, {"published_from": "2020-01-01"})["total"], 0)

    def test_cross_country_homonym_no_match(self):
        a = fixture("a")
        b = fixture("b")
        b["name"] = a["name"]
        b["country"] = "FR"
        with s.connect() as db:
            s.ingest(db, [a, b])
            self.assertEqual(
                db.execute("SELECT count(*) FROM duplicate_review").fetchone()[0], 0
            )
            c = fixture("c")
            c["name"] = "TEST FIXTURE — NOT REAL rebrand"
            s.ingest(db, [c])
            self.assertEqual(
                db.execute("SELECT count(*) FROM duplicate_review").fetchone()[0], 1
            )

    def test_web_urls_and_csv(self):
        for url in (
            "file:///etc/passwd",
            "https://127.0.0.1/",
            "http://169.254.169.254/",
            "http://[::1]/",
            "https://fake.org@localhost/",
        ):
            with self.assertRaises(ValueError):
                s.web_url(url)
        for value in (" =1+1", "\t=2", "@SUM(1)", "-2+3"):
            self.assertTrue(csv_cell(value).startswith("'"))

    def test_transaction_rollback_for_invalid_batch(self):
        with self.assertRaises(ValueError), s.connect() as db:
            s.ingest(db, [fixture(), fixture("bad") | {"evidence": []}])
        with s.connect() as db:
            self.assertFalse(s.load(db))

    def test_suppressed_record_is_not_reingested(self):
        with s.connect() as db:
            db.execute(
                "INSERT INTO metadata VALUES(?,?)", ("suppressed:fixture-only", STAMP)
            )
            counts = s.ingest(db, [fixture()])
            self.assertEqual(counts["discarded"], 1)
            self.assertEqual(s.load(db), [])
