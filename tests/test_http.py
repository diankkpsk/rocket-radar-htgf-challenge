"""TEST FIXTURE — NOT REAL; HTTP tests use a disposable local database."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from backend import jobs, store as s
from backend.api import app
from test_core import fixture


class HTTPTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.env = patch.dict(
            os.environ,
            {"FOUNDER_RADAR_DB": str(Path(self.tmp.name) / "isolated.sqlite3")},
        )
        self.env.start()
        self.sample = fixture()
        self.record = patch("backend.jobs.recordings", return_value=[self.sample])
        self.record.start()
        self.client = TestClient(app)
        self.client.__enter__()

    def tearDown(self):
        self.client.__exit__(None, None, None)
        self.record.stop()
        self.env.stop()
        self.tmp.cleanup()

    def test_start_search_detail_watch_notes_export(self):
        c = self.client
        self.assertEqual(c.get("/health").json()["database"], "ready")
        self.assertEqual(c.get("/").status_code, 200)
        self.assertIn("/api/v1/scans", c.get("/openapi.json").json()["paths"])
        res = c.get("/api/v1/search", params={"q": "pilot"}).json()
        self.assertEqual(res["total"], 1)
        id = res["items"][0]["id"]
        self.assertEqual(c.get(f"/api/v1/leads/{id}/timeline").status_code, 200)
        watched = c.post(f"/api/v1/leads/{id}/watch", json={"watched": True})
        self.assertEqual(watched.status_code, 200, watched.text)
        c.post(
            f"/api/v1/leads/{id}/review",
            json={"note": "Reviewed test", "decision": "accept"},
        )
        self.assertIn(
            "Reviewed test", c.get("/api/v1/exports/leads.csv?watch=true").text
        )
        self.assertIn(
            "https://example.org/fixture", c.get(f"/api/v1/exports/leads/{id}.md").text
        )
        self.assertEqual(c.get("/api/v1/leads/missing").status_code, 404)

    def test_intake_is_manual_and_persisted(self):
        c = self.client
        bad = c.post("/api/v1/import-url", json={"url": "http://127.0.0.1/path"})
        self.assertEqual(bad.status_code, 422)
        self.assertEqual(
            c.post(
                "/api/v1/import-url",
                json={"url": "https://example.com/", "title": "Analyst link"},
            ).status_code,
            201,
        )
        self.assertEqual(len(c.get("/api/v1/imports").json()["items"]), 1)
        self.assertEqual(c.get("/api/v1/stats").json()["prospects"], 1)

    def test_transport_guards_and_input_limits(self):
        c = self.client
        self.assertEqual(
            c.get("/health", headers={"Host": "example.com"}).status_code, 403
        )
        self.assertEqual(
            c.post(
                "/api/v1/settings",
                json={"country": "DE"},
                headers={"Origin": "https://example.com"},
            ).status_code,
            403,
        )
        self.assertEqual(
            c.post(
                "/api/v1/settings",
                content="country=DE",
                headers={"content-type": "text/plain"},
            ).status_code,
            415,
        )
        self.assertEqual(c.get("/api/v1/leads?limit=500").status_code, 422)

    def test_replay_preserves_state_and_source_failure(self):
        data = self.sample
        data["evidence"][0]["source_id"] = "tum"
        job = jobs.reserve("tum", "replay")
        jobs.run(job)
        self.assertEqual(
            self.client.get("/api/v1/scans/" + job["id"]).json()["status"], "success"
        )
        with patch.dict(os.environ, {"COMPANIES_HOUSE_API_KEY": ""}):
            job = jobs.reserve("companies_house", "live")
            jobs.run(job)
        result = self.client.get("/api/v1/scans/" + job["id"]).json()
        self.assertEqual(result["status"], "credential_required")
        self.assertTrue(result["errors"])
        self.assertEqual(
            self.client.post(
                "/api/v1/scans", json={"source_id": "linkedin", "mode": "live"}
            ).status_code,
            422,
        )

    def test_scan_reservation_is_atomic_and_failure_is_visible(self):
        job = jobs.reserve("tum", "live")
        with self.assertRaises(RuntimeError):
            jobs.reserve("norway", "live")
        with patch(
            "backend.jobs.recordings",
            side_effect=ValueError("TEST FIXTURE missing evidence"),
        ):
            jobs.run(job | {"mode": "replay"})
        self.assertEqual(
            self.client.get("/api/v1/scans/" + job["id"]).json()["status"], "failed"
        )

    def test_settings_roundtrip(self):
        r = self.client.post(
            "/api/v1/settings", json={"country": "NL", "priority_threshold": 62}
        )
        self.assertEqual(r.json()["country"], "NL")
        self.assertEqual(
            self.client.get("/api/v1/settings").json()["priority_threshold"], 62
        )

    def test_optional_discovery_and_evaluation(self):
        plan = self.client.get("/api/v1/discovery/plan?country=DE&technology=robotics")
        self.assertEqual(plan.status_code, 200, plan.text)
        self.assertEqual(len(plan.json()["items"]), 14)
        with patch.dict(os.environ, {"BRAVE_SEARCH_API_KEY": ""}):
            result = self.client.post(
                "/api/v1/discovery/web",
                json={"query": "robotics cofounder", "country": "ALL"},
            )
        self.assertEqual(result.status_code, 200, result.text)
        self.assertEqual(result.json()["status"], "credential_required")
        result = self.client.get("/api/v1/evaluation")
        self.assertEqual(result.status_code, 200, result.text)
        self.assertIsNone(result.json()["precision_at_5"]["value"])
