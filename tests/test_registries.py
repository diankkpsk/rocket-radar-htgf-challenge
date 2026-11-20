"""TEST FIXTURE — NOT REAL. All constructed companies and notices exist only in test memory."""

import base64
import csv
import io
import json
import os
import tempfile
import unittest
import zipfile
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

from registries import (
    companies_house,
    coverage,
    german_notice,
    import_estonia,
    norway,
    repository_search,
    to_record,
)
from registries.net import SourceError, _request

LABEL = "TEST FIXTURE — NOT REAL"
UK_ROW = {
    "company_name": LABEL,
    "company_number": "00000001",
    "company_status": "active",
    "company_type": "ltd",
    "date_of_creation": "2025-05-12",
    "sic_codes": ["62012"],
}
EE_COLS = [
    "nimi",
    "ariregistri_kood",
    "ettevotja_esmakande_kpv",
    "ettevotja_oiguslik_vorm",
    "ettevotja_staatus",
]


def uk_rows(rows, hits=None):
    return {"items": rows, "hits": str(len(rows) if hits is None else hits)}


def ee_file(directory, rows, zipped=False):
    data = io.StringIO(newline="")
    writer = csv.writer(data, delimiter=";")
    writer.writerow(EE_COLS)
    writer.writerows(rows)
    if zipped:
        path = Path(directory) / "fixture.zip"
        with zipfile.ZipFile(path, "w") as z:
            z.writestr(
                "ettevotja_rekvisiidid__lihtandmed.csv",
                data.getvalue().encode("utf-8-sig"),
            )
    else:
        path = Path(directory) / "fixture.csv"
        path.write_text(data.getvalue(), encoding="utf-8-sig")
    return path


class CompaniesHouseTests(unittest.TestCase):
    @patch.dict(os.environ, {}, clear=True)
    def test_missing_credential_zero_requests(self):
        b = companies_house(transport=lambda *a: self.fail("attempted network"))
        self.assertEqual(
            (b["status"], b["requests"], b["records"]), ("credential_required", 0, [])
        )

    @patch.dict(os.environ, {"COMPANIES_HOUSE_API_KEY": "pretend-fixture"})
    def test_filtered_dates_pagination_privacy(self):
        seen = []

        def transport(endpoint, params, headers):
            self.assertEqual(endpoint, "companies_house")
            self.assertEqual(params["incorporated_from"], "2025-05-06")
            self.assertEqual(params["incorporated_to"], "2025-05-12")
            self.assertEqual(
                base64.b64decode(headers["Authorization"].split()[1]),
                b"pretend-fixture:",
            )
            seen.append(params["start_index"])
            if len(seen) == 1:
                return uk_rows(
                    [
                        dict(
                            UK_ROW,
                            registered_office_address={
                                "address_line_1": "DO NOT RETAIN"
                            },
                        ),
                        dict(
                            UK_ROW,
                            date_of_creation="2025-05-01",
                            company_number="00000003",
                        ),
                    ],
                    5,
                )
            return uk_rows(
                [
                    dict(UK_ROW),
                    dict(UK_ROW, company_number="00000002", sic_codes=["99999"]),
                ],
                5,
            )

        b = companies_house(
            7, as_of="2025-05-12", page_size=2, max_requests=2, transport=transport
        )
        self.assertEqual((seen, len(b["records"]), b["next_cursor"]), ([0, 2], 1, 4))
        self.assertEqual(
            b["discarded"],
            {
                "outside_window": 1,
                "duplicate_registration": 1,
                "outside_sector_or_legal_form": 1,
            },
        )
        self.assertNotIn("DO NOT RETAIN", json.dumps(b))
        self.assertEqual(b["records"][0]["published_at"], None)

    @patch.dict(os.environ, {"COMPANIES_HOUSE_API_KEY": "pretend-fixture"})
    def test_failures_and_no_hits(self):
        def failing(_, __, ___):
            raise SourceError("HTTP 429", 429, 72)

        b = companies_house(transport=failing)
        self.assertEqual((b["status"], b["retry_after_seconds"]), ("failed", 72))

        def no_hits(_, __, ___):
            raise SourceError("HTTP 404", 404)

        self.assertEqual(companies_house(transport=no_hits)["status"], "success")
        self.assertEqual(
            companies_house(transport=lambda *a: {"unknown": True})["status"], "failed"
        )

    def test_budget_and_date_preflight(self):
        for args in (
            {"days": 91},
            {"as_of": "9999-12-12"},
            {"sic_codes": []},
            {"page_size": 1000},
            {"cursor": -1},
        ):
            with self.assertRaises(ValueError):
                companies_house(**args)


class NorwayTests(unittest.TestCase):
    def test_date_and_sector_checks_before_registration(self):
        good = {
            "organisasjonsnummer": "123456789",
            "navn": LABEL,
            "organisasjonsform": {"kode": "AS"},
            "naeringskode1": {"kode": "62.100"},
            "registreringsdatoEnhetsregisteret": "2025-05-12",
            "stiftelsesdato": "2025-05-06",
        }

        def transport(key, q, headers):
            self.assertEqual(q["fraStiftelsesdato"], "2025-05-06")
            return {
                "_embedded": {
                    "enheter": [
                        good,
                        dict(good, stiftelsesdato="2023-01-02"),
                        dict(good, navn=""),
                        dict(good, organisasjonsform={"kode": "ENK"}),
                    ]
                },
                "page": {"totalElements": 4, "totalPages": 1},
            }

        b = norway(7, as_of="2025-05-12", transport=transport)
        self.assertEqual((len(b["records"]), sum(b["discarded"].values())), (1, 3))
        self.assertEqual(b["records"][0]["formed_at"], "2025-05-06")
        self.assertEqual(b["records"][0]["registered_at"], "2025-05-12")

    def test_legitimate_empty_and_schema_break(self):
        self.assertEqual(
            norway(
                transport=lambda *a: {"page": {"totalElements": 0, "totalPages": 0}}
            )["status"],
            "success",
        )
        self.assertEqual(
            norway(
                transport=lambda *a: {"page": {"totalElements": 3, "totalPages": 1}}
            )["status"],
            "failed",
        )


class EstoniaTests(unittest.TestCase):
    def test_snapshot_csv_and_zip_same_selection(self):
        rows = [
            [LABEL, "12345678", "12.05.2025", "Osaühing", "R"],
            [LABEL, "12345678", "12.05.2025", "Osaühing", "R"],
            [LABEL, "12345679", "12.05.2020", "Aktsiaselts", "R"],
            [LABEL, "12345680", "", "Osaühing", "R"],
            [LABEL, "12345681", "12.05.2025", "Mittetulundusühing", "R"],
        ]
        with tempfile.TemporaryDirectory() as tmp:
            for zipped in (False, True):
                b = import_estonia(
                    ee_file(tmp, rows, zipped),
                    days=7,
                    as_of="2025-05-12",
                    previous_ids={"12345678"},
                )
                self.assertEqual(
                    (b["status"], len(b["records"]), sum(b["discarded"].values())),
                    ("success", 1, 4),
                )
                row = b["records"][0]
                self.assertFalse(row["snapshot_first_appearance"])
                self.assertIsNone(row["published_at"])
                self.assertEqual(row["registered_at"], "2025-05-12")
                self.assertEqual(row["event_type"], "initial_registration")

    def test_wrong_schema_and_scan_caps(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = ee_file(
                tmp,
                [
                    [LABEL, "12345678", "12.05.2025", "Osaühing", "R"],
                    [LABEL, "12345679", "12.05.2025", "Osaühing", "R"],
                ],
            )
            b = import_estonia(p, days=7, as_of="2025-05-12", max_records=1)
            self.assertEqual((b["status"], len(b["records"])), ("partial", 1))
            p.write_text("newtothedataset,entry\n1,today\n")
            self.assertEqual(import_estonia(p)["status"], "failed")
            p = Path(tmp) / "bad.zip"
            with zipfile.ZipFile(p, "w") as z:
                z.writestr("data.csv", "")
                z.writestr("other.txt", "")
            self.assertEqual(import_estonia(p)["status"], "failed")


class ManualAndCoverageTests(unittest.TestCase):
    def notice(self, **fields):
        return {
            "name": LABEL,
            "registration_number": "HRB 12345",
            "court": "TEST COURT",
            "quote": "TEST FIXTURE — NOT REAL",
            "official_url": "https://www.handelsregister.de/rp_web/",
            "event_type": "incorporation",
            "registered_at": date.today().isoformat(),
            "verified": True,
            **fields,
        }

    def test_event_types_and_compound_register_ids(self):
        a = to_record(german_notice(self.notice()))
        b = to_record(german_notice(self.notice(court="ANOTHER TEST COURT")))
        self.assertNotEqual(a["id"], b["id"])
        self.assertEqual(a["stage"], "NEWLY_INCORPORATED")
        self.assertEqual(a["funding_status"], "UNKNOWN")
        self.assertEqual(a["team"], [])
        for kind in ("branch", "amendment", "relocation", "publication", "unknown"):
            row = to_record(
                german_notice(
                    self.notice(
                        event_type=kind,
                        registered_at=None,
                        published_at=date.today().isoformat(),
                    )
                )
            )
            self.assertEqual(row["stage"], "UNKNOWN")
            self.assertIsNone(row["evidence"][0]["event_date"])
            self.assertEqual(row["evidence"][0]["signal_type"], "OTHER")
        self.assertEqual(
            to_record(
                german_notice(
                    self.notice(
                        registered_at=(date.today() - timedelta(days=90)).isoformat()
                    )
                )
            )["stage"],
            "UNKNOWN",
        )

    def test_notice_validation(self):
        for fields in (
            {"event_type": "amendment"},
            {"verified": False},
            {"registered_at": None},
            {"registered_at": "2024-11-31"},
            {"official_url": "https://www.handelsregister.de.example/rp_web/"},
            {
                "official_url": "https://www.handelsregister.de/rp_web/foo;jsessionid=secret"
            },
            {"official_url": "https://username:secret@www.handelsregister.de/rp_web/"},
            {"official_url": "http://localhost:80/"},
            {"registration_number": "nonsense"},
        ):
            with self.assertRaises(ValueError):
                german_notice(self.notice(**fields))

    def test_searchable_directory_with_capabilities(self):
        rows = coverage()
        self.assertEqual(len(rows), len({r["country_code"] for r in rows}))
        self.assertGreaterEqual(len(rows), 49)
        self.assertEqual(coverage("Norway")[0]["status"], "live")
        self.assertEqual(coverage("Slovenia")[0]["status"], "planned")
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(
                coverage("United Kingdom")[0]["status"], "credential_required"
            )


class DeveloperTests(unittest.TestCase):
    def test_only_public_repos_and_no_founder_inference(self):
        good = {
            "full_name": "test-fixture/fiction",
            "html_url": "https://github.com/test-fixture/fiction",
            "private": False,
            "description": LABEL,
            "owner": {"type": "User", "login": "fixture-person"},
            "stargazers_count": 900,
        }

        def transport(key, q, headers):
            self.assertIn("is:public", q["q"])
            return {
                "items": [
                    good,
                    dict(good, private=True),
                    dict(good, html_url="http://example.invalid"),
                ],
                "total_count": 3,
            }

        b = repository_search("fixture academic prototype", transport=transport)
        self.assertEqual(len(b["records"]), 1)
        self.assertIsNone(b["records"][0]["organization"])
        self.assertNotIn("founder", b["records"][0])
        self.assertNotIn("stage", b["records"][0])
        self.assertNotIn("fixture-person", json.dumps(b))
        with self.assertRaises(ValueError):
            repository_search("fixture is:private")

    @patch(
        "registries.net.socket.getaddrinfo",
        return_value=[(2, 1, 6, "", ("127.0.0.1", 443))],
    )
    def test_public_connection_pinning(self, _):
        with self.assertRaisesRegex(SourceError, "public address"):
            _request("api.github.com", "/search/repositories", {})


if __name__ == "__main__":
    unittest.main()
