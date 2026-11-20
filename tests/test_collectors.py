"""Parser regressions. All invented inputs are TEST FIXTURE — NOT REAL."""

import json
from pathlib import Path
import unittest
from unittest.mock import Mock

from collectors import htgf, kit, tum
from collectors.fetch import CollectionError, Fetcher
from collectors.reviewed import apply

STAMP = "2026-11-20T14:00:00Z"
ROOT = Path(__file__).resolve().parents[1]
FIXTURE = "TEST FIXTURE — NOT REAL"


class CollectorTests(unittest.TestCase):
    def test_htgf_old_taxonomy_and_html_entities(self):
        raw = [
            {
                "id": 1,
                "lang": "en",
                "link": "https://www.htgf.de/en/portfolio/test-fixture/",
                "title": {"rendered": FIXTURE + " A &amp; B (Exit)"},
                "date_gmt": "2018-04-10T09:45:27",
                "class_list": ["portfolio", "branchen22-optics-photonics"],
                "content": {"rendered": "<script>TEST FIXTURE — NOT REAL</script>"},
            }
        ]
        item = htgf.parse_page(raw, STAMP)[0]
        self.assertIn("A & B (Exit)", item["name"])
        self.assertEqual(item["sector"], "Optics photonics")
        self.assertEqual(item["stage"], "UNKNOWN")
        self.assertEqual(item["kind"], "portfolio")
        self.assertEqual(item["evidence"][0]["published_at"], "2018-04-10T09:45:27Z")
        self.assertIsNone(item["evidence"][0]["event_date"])
        self.assertIsNone(item["country"])
        self.assertIsNone(item["website"])
        self.assertEqual(item["evidence"][0]["quote"], item["name"])
        raw[0]["link"] = "https://example.org/not-portfolio"
        with self.assertRaises(CollectionError):
            htgf.parse_page(raw, STAMP)

    def test_htgf_rejects_overlapping_pages(self):
        def page_item(k):
            return {
                "id": k,
                "lang": "en",
                "title": {"rendered": FIXTURE + str(k)},
                "link": "https://www.htgf.de/en/portfolio/test-fixture/",
                "class_list": ["portfolio"],
            }

        payload = json.dumps([page_item(i) for i in range(100)])
        fetcher = Mock()
        fetcher.get.side_effect = [payload, payload]
        with self.assertRaisesRegex(CollectionError, "Overlapping"):
            htgf.collect(fetcher)

    def test_tum_only_reads_finalists_and_keeps_unknown_dates(self):
        name = FIXTURE
        panel = (
            '<div class="in2template-accordion" id="c123">'
            '<span class="in2template-accordion__title">' + name + "</span>"
            '<div class="in2template-accordion__panel">TEST FIXTURE — NOT REAL. A test concept.</div></div>'
        )
        html = (
            "<h2>FAQ</h2>"
            + panel
            + "<h2>The finalists of the TUM IDEAward 2026 in brief</h2>"
            + panel
        )
        html += "<h2>Archive</h2>" + panel
        rows = tum.parse(html, STAMP)
        self.assertEqual([r["name"] for r in rows], [name])
        ev = rows[0]["evidence"][0]
        self.assertTrue(ev["url"].endswith("#c123"))
        self.assertIsNone(ev["published_at"])
        self.assertIsNone(ev["event_date"])
        self.assertIsNone(rows[0]["country"])
        with self.assertRaises(CollectionError):
            tum.parse("<html>Unexpected source format</html>", STAMP)

    def test_kit_only_follows_canonical_founder_profiles(self):
        title = "Founder of the month: " + FIXTURE
        a = (
            '<a class="flowTeaser__item" href="/en/magazine/founder-of-the-month-fixture/">'
            '<span class="flowTeaser__category">Founder of the month</span><div class="h3">'
            + title
            + "</div></a>"
        )
        links = kit.index(a + a)
        self.assertEqual(len(links), 1)
        self.assertTrue(links[0].startswith("https://www.kit-forge.de/en/magazine/"))
        html = (
            "<h1>" + title + '</h1><span class="articleIntro__date">02.03.2026</span>'
            '<figcaption class="teaserImage__caption">TEST FIXTURE — NOT REAL. An invented project.</figcaption>'
        )
        row = kit.parse(html, links[0], STAMP)
        self.assertEqual(row["evidence"][0]["published_at"], "2026-03-02")
        self.assertEqual(row["team"], [])
        self.assertIsNone(row["website"])
        with self.assertRaises(CollectionError):
            kit.index(a.replace('href="/en/', 'href="https://example.org/en/'))

    def test_recorded_research_reuses_original_clocks(self):
        rows = json.loads((ROOT / "data" / "records.json").read_text())
        stored = next(r for r in rows if r.get("best_find"))
        new = dict(
            stored, evidence=[e for e in stored["evidence"] if e["source_id"] == "tum"]
        )
        refreshed = apply([new])[0]
        self.assertEqual(refreshed["evidence"], stored["evidence"])
        self.assertEqual(
            {e["source_id"] for e in stored["evidence"]},
            {"tum", "chemanager", "mit_cep", "baystartup"},
        )
        self.assertEqual(stored["registration_status"], "NOT_VERIFIED")
        self.assertIsNone(stored["website"])
        self.assertEqual(
            {p["name"] for p in stored["team"]}, {"Alba Impelmann", "Mark Deeprose"}
        )

    def test_packaged_capture_integrity(self):
        rows = json.loads((ROOT / "data" / "records.json").read_text())
        self.assertEqual(len(rows), len({r["id"] for r in rows}))
        self.assertEqual(sum(r["kind"] == "portfolio" for r in rows), 541)
        self.assertEqual(sum(r["kind"] == "prospect" for r in rows), 16)
        for r in rows:
            self.assertNotIn(FIXTURE, r["name"])
            for e in r["evidence"]:
                self.assertTrue(
                    e["quote"] and e["claim"] and e["url"].startswith("https://")
                )
                self.assertLessEqual(e["first_observed_at"], e["retrieved_at"])
            if r["kind"] == "portfolio":
                self.assertEqual(r["stage"], "UNKNOWN")

    def test_fetcher_rejects_unknown_host_before_network(self):
        with self.assertRaises(CollectionError):
            Fetcher().get("https://example.org/")
