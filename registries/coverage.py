"""Searchable directory with separate status for each implemented capability."""

import csv
import os
from pathlib import Path

CH_DOCS = "https://developer-specs.company-information.service.gov.uk/companies-house-public-data-api/reference/search/advanced-company-search"
EE_DOCS = "https://avaandmed.ariregister.rik.ee/en/downloading-open-data"
NO_DOCS = "https://data.brreg.no/enhetsregisteret/api/dokumentasjon/en/index.html"
DE_DOCS = "https://www.handelsregister.de/rp_web/information/welcome.xhtml"


def coverage(query=""):
    if not isinstance(query, str) or len(query) > 160:
        raise ValueError("The optional coverage search must be at most 160 characters.")
    q = query.strip().casefold()
    has_key = bool(os.environ.get("COMPANIES_HOUSE_API_KEY"))
    adapters = {
        "GB": (
            "companies_house",
            "configured" if has_key else "credential_required",
            "API key required",
            CH_DOCS,
            "Verified on public pages. The API adapter was contract-tested. Set COMPANIES_HOUSE_API_KEY to run it.",
            "Government open data; review current Companies House terms.",
            "Incorporation date",
            "Request-time lookup",
        ),
        "EE": (
            "estonia",
            "manual_only",
            "Local snapshot import",
            EE_DOCS,
            "Import an operator-downloaded basic-data CSV or ZIP file. Automated downloads are disabled.",
            "Review and accept the terms on the official download page.",
            "Date of first entry",
            "Daily source snapshot",
        ),
        "DE": (
            "german_register",
            "manual_only",
            "Manual verification",
            DE_DOCS,
            "An analyst transcribes an official notice and its register court. Automated portal collection is disabled.",
            "Registerportal conditions of use apply.",
            "Initial entry when explicit in the notice",
            "Manual",
        ),
        "NO": (
            "norway",
            "live",
            "Public API",
            NO_DOCS,
            "Date-window search of AS entities with selected industry codes. Both first registration and formation are checked.",
            "Norwegian Licence for Open Government Data (NLOD) 2.0.",
            "First CCR registration and formation",
            "Request-time lookup",
        ),
    }
    with (
        Path(__file__)
        .with_name("directory.csv")
        .open(encoding="utf-8", newline="") as fp
    ):
        out = []
        for entry in csv.DictReader(fp):
            code, country, name, url = (
                entry[k] for k in ("code", "country", "name", "url")
            )
            values = adapters.get(
                code,
                (
                    None,
                    "planned",
                    "Directory only",
                    None,
                    "Research starting point from the project brief. Programmatic access and reuse terms have not been validated.",
                    None,
                    None,
                    None,
                ),
            )
            key, status, mode, docs, notes, license_notes, date_field, cadence = values
            row = {
                "country_code": code,
                "country": country,
                "name": name,
                "url": url,
                "registry": name,
                "source_id": key,
                "status": status,
                "mode": mode,
                "docs_url": docs,
                "notes": notes,
                "license_notes": license_notes,
                "registration_date": date_field,
                "cadence": cadence,
                "costs": None,
                "automated_discovery": code in ("NO", "GB"),
                "credential_configured": has_key if code == "GB" else None,
            }
            if not q or any(
                q in str(row[k]).casefold()
                for k in ("country_code", "country", "name", "status", "mode")
            ):
                out.append(row)
    return out
