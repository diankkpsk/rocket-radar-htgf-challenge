"""All provider responses and projects below are TEST FIXTURE — NOT REAL."""

import os
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

from backend import discovery as d


class QueryPlannerTests(unittest.TestCase):
    def test_plans_are_bounded_multilingual_and_offline(self):
        with patch.object(
            d.net, "_request", side_effect=AssertionError("Unexpected request")
        ):
            rows = d.plan("de", "photonic chips", 42)["items"]
        self.assertEqual(len({row["query"] for row in rows}), 42)
        self.assertEqual({row["language"] for row in rows[:7]}, set(d.INTENT))
        self.assertEqual(rows[0]["language"], "de")
        for row in rows:
            self.assertIn("photonic chips", row["query"])
            self.assertIn(f"lang:{row['language']}", row["query"])
            self.assertTrue(
                any(f'"{term}"' in row["query"] for term in d.INTENT[row["language"]])
            )
        self.assertIn("site:de", rows[1]["query"])
        self.assertIn("Deutschland", rows[0]["query"])
        self.assertIn("site:uk", d.plan("GB")["items"][1]["query"])
        self.assertEqual(d.plan("all", "", 1)["items"][0]["scope"], "web")

    def test_input_validation(self):
        for args in (
            ("DE", "", 43),
            ("DE", "", 0),
            ("ZZ", "", 1),
            ("DE", "a\nb", 1),
            ("DE", "x " * 25, 1),
            ("DE", "x" * 101, 1),
        ):
            with self.subTest(args=args), self.assertRaises(ValueError):
                d.plan(*args)
        for q in ("", "x " * 41, "x" * 301, "a\nb"):
            with self.subTest(q=q), self.assertRaises(ValueError):
                d.web_search(q)


class SearchTests(unittest.TestCase):
    def setUp(self):
        self.enterContext(
            patch.dict(os.environ, {"BRAVE_SEARCH_API_KEY": "test-fixture-token"})
        )
        self.enterContext(patch.object(d, "_next_request", 0))
        self.request = self.enterContext(patch.object(d.net, "_request"))

    def test_missing_key_has_manual_intake_and_no_request(self):
        with patch.dict(os.environ, {"BRAVE_SEARCH_API_KEY": ""}):
            result = d.web_search("a project")
            self.assertFalse(d.plan()["configured"])
        self.assertEqual(result["status"], "credential_required")
        self.assertEqual(result["manual_intake"], "/api/v1/import-url")
        self.request.assert_not_called()

    def test_fixed_destination_and_bounded_results(self):
        row = {
            "title": "Optics &amp; sensors",
            "description": "x" * 1000,
            "url": "https://venture.example/project",
        }
        self.request.return_value = {
            "web": {
                "results": [
                    row,
                    row,
                    {"url": "javascript:alert(1)"},
                    {"url": "https://127.0.0.1/x"},
                    {"url": "https://second.example/", "title": None},
                    {"url": "https://unrequested.example/"},
                ]
            }
        }
        result = d.web_search("site:de photonics & sensors lang:de", "DE")
        host, path, headers = self.request.call_args.args
        self.assertEqual(host, "api.search.brave.com")
        self.assertEqual(urlsplit(path).path, "/res/v1/web/search")
        params = parse_qs(urlsplit(path).query)
        self.assertEqual(params["q"], ["site:de photonics & sensors lang:de"])
        self.assertEqual(params["country"], ["DE"])
        self.assertEqual(params["search_lang"], ["de"])
        self.assertEqual(params["count"], ["5"])
        self.assertEqual(headers["X-Subscription-Token"], "test-fixture-token")
        self.assertNotIn("test-fixture-token", str(result) + path)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(len(result["items"]), 2)
        self.assertEqual(result["items"][0]["title"], "Optics & sensors")
        self.assertEqual(len(result["items"][0]["description"]), 450)
        self.request.assert_called_once()

    def test_unsupported_region_keeps_location(self):
        self.request.return_value = {}
        self.assertEqual(d.web_search("pilot customers", "EE")["items"], [])
        params = parse_qs(urlsplit(self.request.call_args.args[1]).query)
        self.assertEqual(params["country"], ["ALL"])
        self.assertIn('"Estonia"', params["q"][0])

    def test_rate_limit_blocks_subsequent_request(self):
        self.request.side_effect = d.net.SourceError("Provider response", 429, 60)
        result = d.web_search("chip project")
        self.assertEqual(
            (result["status"], result["retry_after"]), ("rate_limited", 60)
        )
        self.assertEqual(d.web_search("second query")["status"], "rate_limited")
        self.request.assert_called_once()

    def test_errors_are_transient_and_do_not_expose_provider_data(self):
        for problem, expected in [
            (d.net.SourceError("private response", 401), "credential_required"),
            (OSError("private response"), "unavailable"),
        ]:
            with self.subTest(problem=problem), patch.object(d, "_next_request", 0):
                self.request.side_effect = problem
                result = d.web_search("chip project")
                self.assertEqual(result["status"], expected)
                self.assertNotIn("private response", str(result))
        self.request.side_effect = None
        self.request.return_value = {"web": {"results": "broken"}}
        self.assertEqual(d.web_search("chip project")["status"], "unavailable")
