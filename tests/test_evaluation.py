"""Evaluation metrics using an isolated database. All entries are TEST FIXTURE — NOT REAL."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend import evaluation, store
from test_core import fixture


class EvaluationTests(unittest.TestCase):
    def setUp(self):
        tmp = self.enterContext(tempfile.TemporaryDirectory())
        self.enterContext(
            patch.dict(os.environ, {"FOUNDER_RADAR_DB": str(Path(tmp) / "eval.db")})
        )
        store.init()
        self.db = self.enterContext(store.connect())

    def test_empty_workspace_has_no_measured_rates(self):
        report = evaluation.report(self.db)
        self.assertEqual(report["precision_at_5"]["reason"], "insufficient_prospects")
        for field in ("precision_at_5", "precision_at_10"):
            self.assertIsNone(report[field]["value"])
        self.assertIsNone(report["signal_latency"]["median_days"])
        self.assertIsNone(report["duplicates"]["review_completion_rate"])
        self.assertIsNone(report["scan_health"]["full_success_rate"])

    def test_labels_must_cover_every_ranked_slot(self):
        prospects = [fixture(f"prospect-{i:02d}") for i in range(11)]
        store.ingest(
            self.db, prospects + [fixture("reference") | {"kind": "portfolio"}]
        )
        feed = store.search(self.db, {})["items"]
        ids = [r["id"] for r in feed]
        for id_ in ids[:4] + ids[5:]:
            store.set_review(self.db, id_, {"decision": "accept"})
        store.set_review(self.db, ids[4], {"decision": "watch"})
        result = evaluation.report(self.db)
        self.assertEqual(result["population"]["portfolio_excluded"], 1)
        self.assertEqual(result["precision_at_10"]["ranked_ids"], ids[:10])
        self.assertIsNone(result["precision_at_5"]["value"])
        self.assertIsNone(result["precision_at_10"]["value"])
        self.assertEqual(result["precision_at_5"]["labelled"], 4)
        store.set_review(self.db, ids[4], {"decision": "reject"})
        result = evaluation.report(self.db)
        self.assertEqual(result["precision_at_5"]["value"], 0.8)
        self.assertEqual(result["precision_at_10"]["value"], 0.9)
        store.set_review(self.db, ids[6], {"decision": "review"})
        result = evaluation.report(self.db)
        self.assertEqual(result["precision_at_5"]["value"], 0.8)
        self.assertIsNone(result["precision_at_10"]["value"])

    def test_latency_groups_one_publication_and_preserves_unknown_dates(self):
        project = fixture()
        base = project["evidence"][0] | {
            "published_at": "2025-05-01",
            "event_date": "2020-01-01",
            "first_observed_at": "2025-05-11",
            "retrieved_at": "2025-10-11",
        }
        project["evidence"] = [
            base,
            base | {"quote": "A second observation in the same article."},
            base | {"url": "https://example.org/nodate", "published_at": None},
            base
            | {"url": "https://example.org/negative", "published_at": "2025-05-20"},
            base | {"url": "https://example.org/conflict"},
            base
            | {
                "url": "https://example.org/conflict",
                "published_at": "2025-06-01",
                "quote": "Other signal.",
            },
        ]
        store.ingest(self.db, [project], "replay")
        metrics = evaluation.report(self.db)["signal_latency"]
        self.assertEqual(metrics["median_days"], 10)
        self.assertEqual(metrics["total"], 4)
        for field in (
            "measured",
            "missing_dates",
            "conflicting_publication_dates",
            "observed_before_publication",
        ):
            self.assertEqual(metrics[field], 1, field)

    def test_duplicate_queue_and_live_scan_denominators(self):
        store.ingest(self.db, [fixture("a"), fixture("b"), fixture("c")])
        self.db.execute(
            "UPDATE duplicate_review SET decision='related' WHERE left_id='a' AND right_id='b'"
        )
        scans = [
            ("live", "success", 0),
            ("replay", "success", 99),
            ("live", "partial", 3),
            ("live", "failed", 0),
            ("live", "credential_required", 0),
        ]
        self.db.executemany(
            "INSERT INTO scans(id,source_id,started_at,mode,status,discarded) "
            "VALUES(?,'test','2026-01-01',?,?,?)",
            [(str(i), *s) for i, s in enumerate(scans)],
        )
        report = evaluation.report(self.db)
        self.assertEqual(report["duplicates"]["review_completion_rate"], 1 / 3)
        self.assertIsNone(report["duplicates"]["confirmed_entity_duplicate_rate"])
        self.assertEqual(report["scan_health"]["full_success_rate"], 1 / 3)
        self.assertEqual(report["scan_health"]["live_discarded_records"], 3)
        self.assertEqual(report["scan_health"]["replay_runs"], 1)
        self.assertIsNone(report["scan_health"]["parser_error_rate"])
