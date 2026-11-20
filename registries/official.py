"""Official registry adapters and normalized legal records. Python 3.12 standard library."""

from __future__ import annotations

import base64
import csv
import hashlib
import io
import json
import os
import re
import zipfile
from collections import Counter
from contextlib import contextmanager, ExitStack
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit

from .net import SourceError, fetch, utcnow

SOURCE_NAMES = {
    "companies_house": "Companies House",
    "estonia": "Estonian e-Business Register",
    "german_register": "German register portal",
    "norway": "Brønnøysund Register Centre",
}
DEFAULT_SIC = ("72190", "62012", "71121", "26110")


def _today():
    return datetime.now(timezone.utc).date()


def _day(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def _bounds(days, as_of):
    if days not in (7, 30, 90) or type(days) is not int:
        raise ValueError("Choose a 7, 30 or 90 day registration window.")
    end = _today() if as_of is None else _day(as_of)
    if end is None or end > _today():
        raise ValueError("as_of must be a valid ISO calendar date through today.")
    return end - timedelta(days=days - 1), end


def _limit(number, low, high, label):
    if type(number) is not int or not low <= number <= high:
        raise ValueError(f"{label} must be between {low} and {high}.")
    return number


def _plain(value, limit=200):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        return None
    return " ".join(value.split())


def _batch(source):
    return {
        "source_key": source,
        "records": [],
        "status": "success",
        "errors": [],
        "requests": 0,
        "records_parsed": 0,
        "discarded": {},
        "next_cursor": None,
        "retrieved_at": None,
    }


def _fail(b, error):
    b["status"] = "partial" if b["records"] else "failed"
    b["errors"].append(str(error))
    if isinstance(error, SourceError) and error.retry_after is not None:
        b["retry_after_seconds"] = error.retry_after
    return b


def _legal(source, code, name, number, date_value, url, retrieved, **extra):
    return {
        "source_key": source,
        "country_code": code,
        "name": name,
        "registration_number": number,
        "registered_at": date_value,
        "official_url": url,
        "retrieved_at": retrieved,
        "first_observed_at": retrieved,
        "published_at": None,
        "industry_codes": [],
        "event_type": "incorporation",
        "registration_status": "VERIFIED_REGISTERED",
        "funding_status": "UNKNOWN",
        "qualification": "venture potential requires review",
        **extra,
    }


def companies_house(
    days=7,
    *,
    as_of=None,
    sic_codes=DEFAULT_SIC,
    cursor=0,
    page_size=20,
    max_requests=2,
    transport=fetch,
):
    start, end = _bounds(days, as_of)
    _limit(cursor, 0, 5000, "Cursor")
    _limit(max_requests, 1, 3, "Request budget")
    _limit(page_size, 1, 40, "Page size")
    if (
        isinstance(sic_codes, str)
        or not isinstance(sic_codes, (tuple, list))
        or not 1 <= len(sic_codes) <= 8
        or any(
            not isinstance(s, str) or not re.fullmatch(r"\d{5}", s) for s in sic_codes
        )
    ):
        raise ValueError("Supply one to eight five-digit UK SIC codes.")
    b = _batch("companies_house")
    b["window"] = [start.isoformat(), end.isoformat()]
    key = os.environ.get("COMPANIES_HOUSE_API_KEY")
    if not key:
        b.update(
            status="credential_required",
            errors=["Set COMPANIES_HOUSE_API_KEY to run a live UK scan."],
        )
        return b
    auth = base64.b64encode((key + ":").encode()).decode()
    seen = set()
    discarded = Counter()
    for _ in range(max_requests):
        query = {
            "incorporated_from": start.isoformat(),
            "incorporated_to": end.isoformat(),
            "sic_codes": list(sic_codes),
            "company_type": ["ltd", "plc"],
            "company_status": "active",
            "size": page_size,
            "start_index": cursor,
        }
        b["requests"] += 1
        try:
            page = transport(
                "companies_house", query, {"Authorization": "Basic " + auth}
            )
        except SourceError as err:
            if err.status == 404:
                b["next_cursor"] = None
                break
            return _fail(b, err)
        now = utcnow()
        b["retrieved_at"] = now
        rows = page.get("items")
        if not isinstance(rows, list) or len(rows) > page_size:
            return _fail(b, "Unexpected items in Companies House response.")
        for row in rows:
            b["records_parsed"] += 1
            if not isinstance(row, dict):
                discarded["invalid_record"] += 1
                continue
            number, name = (
                row.get("company_number"),
                _plain(row.get("company_name"), 300),
            )
            created = _day(row.get("date_of_creation"))
            codes = row.get("sic_codes")
            if (
                not name
                or not isinstance(number, str)
                or not re.fullmatch(r"[A-Z0-9]{8}", number)
                or not created
            ):
                discarded["missing_identity_or_date"] += 1
            elif number in seen:
                discarded["duplicate_registration"] += 1
            elif not start <= created <= end:
                discarded["outside_window"] += 1
            elif (
                row.get("company_type") not in ("ltd", "plc")
                or row.get("company_status") != "active"
                or not isinstance(codes, list)
                or not any(c in sic_codes for c in codes)
            ):
                discarded["outside_sector_or_legal_form"] += 1
            else:
                seen.add(number)
                b["records"].append(
                    _legal(
                        "companies_house",
                        "GB",
                        name,
                        number,
                        created.isoformat(),
                        f"https://find-and-update.company-information.service.gov.uk/company/{number}",
                        now,
                        status="active",
                        legal_form=row["company_type"],
                        industry_codes=[c for c in codes if isinstance(c, str)],
                        quote=created.isoformat(),
                        capture_mode="official_api",
                        excerpt_type="JSON field",
                        summary="Companies House records an incorporation in the selected industrial classification. Product and traction evidence remain open.",
                    )
                )
        b["discarded"] = dict(discarded)
        cursor += len(rows)
        hits = str(page.get("hits", ""))
        if (
            len(rows) < page_size
            or (hits.isdigit() and cursor >= int(hits))
            or cursor > 5000
        ):
            b["next_cursor"] = None
            break
        b["next_cursor"] = cursor
    return b


def norway(days=7, *, as_of=None, cursor=0, page_size=20, transport=fetch):
    start, end = _bounds(days, as_of)
    _limit(cursor, 0, 100, "Page")
    _limit(page_size, 1, 40, "Page size")
    b = _batch("norway")
    b["window"] = [start.isoformat(), end.isoformat()]
    # Both the foundation and first CCR registration must fall in the selected period.
    query = {
        "fraRegistreringsdatoEnhetsregisteret": start.isoformat(),
        "tilRegistreringsdatoEnhetsregisteret": end.isoformat(),
        "fraStiftelsesdato": start.isoformat(),
        "tilStiftelsesdato": end.isoformat(),
        "organisasjonsform": "AS",
        "naeringskode": "62.1,72.1,26.1",
        "page": cursor,
        "size": page_size,
    }
    b["requests"] = 1
    try:
        page = transport(
            "norway", query, {"Accept": "application/json, application/hal+json"}
        )
    except SourceError as err:
        return _fail(b, err)
    info = page.get("page")
    embedded = page.get("_embedded", {})
    now = utcnow()
    if not isinstance(info, dict) or not isinstance(embedded, dict):
        return _fail(b, "Unexpected Norway API page schema.")
    entities = embedded.get("enheter", [])
    if (
        not isinstance(entities, list)
        or len(entities) > page_size
        or not isinstance(info.get("totalPages"), int)
        or (not entities and info.get("totalElements") and cursor < info["totalPages"])
    ):
        return _fail(b, "Unexpected Norway entity listing.")
    b["retrieved_at"] = now
    b["next_cursor"] = (
        cursor + 1 if cursor + 1 < info["totalPages"] and cursor < 100 else None
    )
    rejected = Counter()
    seen = set()
    for row in entities:
        b["records_parsed"] += 1
        if not isinstance(row, dict):
            rejected["invalid_record"] += 1
            continue
        number, name = row.get("organisasjonsnummer"), _plain(row.get("navn"), 300)
        formation, registered = (
            _day(row.get("stiftelsesdato")),
            _day(row.get("registreringsdatoEnhetsregisteret")),
        )
        form, industry = (
            row.get("organisasjonsform") or {},
            row.get("naeringskode1") or {},
        )
        if (
            not isinstance(number, str)
            or not re.fullmatch(r"\d{9}", number)
            or not name
            or not formation
            or not registered
        ):
            rejected["missing_identity_or_dates"] += 1
        elif not (start <= formation <= registered <= end):
            rejected["outside_formation_or_registration_window"] += 1
        elif not (
            isinstance(form, dict)
            and form.get("kode") == "AS"
            and isinstance(industry, dict)
            and str(industry.get("kode")).startswith(("62.1", "72.1", "26.1"))
        ):
            rejected["outside_sector_or_legal_form"] += 1
        elif number in seen:
            rejected["duplicate_registration"] += 1
        else:
            seen.add(number)
            b["records"].append(
                _legal(
                    "norway",
                    "NO",
                    name,
                    number,
                    registered.isoformat(),
                    f"https://data.brreg.no/enhetsregisteret/api/enheter/{number}",
                    now,
                    formed_at=formation.isoformat(),
                    legal_form="AS",
                    event_type="initial_registration",
                    industry_codes=[industry["kode"]],
                    quote=registered.isoformat(),
                    excerpt_type="JSON field",
                    capture_mode="official_api",
                    summary="The Norwegian register records the company formation and initial registration. Its commercial progress requires investigation.",
                )
            )
    b["discarded"] = dict(rejected)
    return b


@contextmanager
def _open_estonia(path):
    path = Path(path)
    if not path.is_file():
        raise ValueError(
            "Supply a local basic-data CSV file or its original ZIP archive."
        )
    with ExitStack() as stack:
        if path.suffix.lower() == ".zip":
            if path.stat().st_size > 50 * 1024**2:
                raise ValueError("ZIP archive exceeds 50 MiB.")
            archive = stack.enter_context(zipfile.ZipFile(path))
            contents = [i for i in archive.infolist() if not i.is_dir()]
            if len(contents) != 1 or not contents[0].filename.lower().endswith(".csv"):
                raise ValueError("Use a ZIP containing one basic-data CSV.")
            meta = contents[0]
            if meta.file_size > 256 * 1024**2 or meta.flag_bits & 1:
                raise ValueError("CSV exceeds 256 MiB or the archive is encrypted.")
            binary = stack.enter_context(
                archive.open(meta)
            )  # No member is ever extracted to disk.
        elif path.suffix.lower() == ".csv" and path.stat().st_size <= 256 * 1024**2:
            binary = stack.enter_context(path.open("rb"))
        else:
            raise ValueError("Use a CSV up to 256 MiB or its ZIP archive.")
        stream = stack.enter_context(
            io.TextIOWrapper(binary, encoding="utf-8-sig", newline="")
        )
        first = stream.readline(4097)
        if not first or len(first) > 4096:
            raise ValueError("Missing or oversized CSV header.")
        delimiter = ";" if first.count(";") > first.count(",") else ","
        header = [s.strip() for s in next(csv.reader([first], delimiter=delimiter))]
        required = {
            "ariregistri_kood",
            "nimi",
            "ettevotja_esmakande_kpv",
            "ettevotja_oiguslik_vorm",
            "ettevotja_staatus",
        }
        if not required.issubset(header) or len(set(header)) != len(header):
            raise ValueError(
                "Unexpected file schema. Download the basic data (Lihtandmed) CSV."
            )

        # Reject oversized individual lines before the CSV parser creates row structures.
        def lines():
            while True:
                line = stream.readline(65537)
                if not line:
                    break
                if len(line) > 65536:
                    raise ValueError("A CSV row exceeds the 64 KiB limit.")
                yield line

        yield csv.DictReader(
            lines(), fieldnames=header, delimiter=delimiter, strict=True
        )


def import_estonia(
    path, *, days=90, as_of=None, max_records=100, max_rows=500000, previous_ids=None
):
    """Import an operator-selected official CSV snapshot, after its licence is accepted at source."""
    start, end = _bounds(days, as_of)
    _limit(max_records, 1, 500, "Result budget")
    _limit(max_rows, 1, 500000, "Row budget")
    b = _batch("estonia")
    b["window"] = [start.isoformat(), end.isoformat()]
    now = utcnow()
    seen = set()
    rejected = Counter()
    b["mode"] = "local_snapshot"
    try:
        with _open_estonia(path) as rows:
            for i, row in enumerate(rows):
                if i >= max_rows or len(b["records"]) >= max_records:
                    b["status"] = "partial"
                    b["errors"].append(
                        "Reached the scan budget; snapshot coverage is partial."
                    )
                    break
                b["records_parsed"] += 1
                number = row.get("ariregistri_kood", "").strip()
                name = _plain(row.get("nimi"), 300)
                stamp = (row.get("ettevotja_esmakande_kpv") or "").strip()
                form = (row.get("ettevotja_oiguslik_vorm") or "").strip()
                status = (row.get("ettevotja_staatus") or "").strip()
                try:
                    registered = (
                        datetime.strptime(stamp, "%d.%m.%Y").date()
                        if "." in stamp
                        else _day(stamp)
                    )
                except ValueError:
                    registered = None
                if not re.fullmatch(r"\d{8}", number) or not name or not registered:
                    rejected["missing_identity_or_first_entry"] += 1
                elif not start <= registered <= end:
                    rejected["outside_registration_window"] += 1
                elif (
                    form.casefold()
                    not in {
                        "osaühing",
                        "aktsiaselts",
                        "oü",
                        "as",
                        "private limited company",
                        "public limited company",
                    }
                    or status != "R"
                ):
                    rejected["outside_company_form_or_status"] += 1
                elif number in seen:
                    rejected["duplicate_registration"] += 1
                else:
                    seen.add(number)
                    b["records"].append(
                        _legal(
                            "estonia",
                            "EE",
                            name,
                            number,
                            registered.isoformat(),
                            f"https://ariregister.rik.ee/eng/company/{number}",
                            now,
                            event_type="initial_registration",
                            legal_form=form,
                            status=status,
                            quote=stamp,
                            excerpt_type="First-entry CSV field",
                            capture_mode="local_official_snapshot",
                            snapshot_as_of=as_of,
                            snapshot_first_appearance=None
                            if previous_ids is None
                            else number not in previous_ids,
                            summary="The Estonian basic-data snapshot records a first register entry for a limited company. Venture qualification is open.",
                        )
                    )
    except (OSError, csv.Error, UnicodeError, zipfile.BadZipFile, ValueError) as err:
        # Do not return partially parsed data after an invalid file or corrupt ZIP member.
        b["records"] = []
        return _fail(b, f"Snapshot could not be imported. {err}")
    b["discarded"] = dict(rejected)
    b["retrieved_at"] = now
    return b


NOTICE_TYPES = {
    "incorporation",
    "amendment",
    "relocation",
    "branch",
    "publication",
    "unknown",
}


def german_notice(payload):
    """Record an analyst's manual verification. Never fetch the submitted link."""
    if not isinstance(payload, dict):
        raise ValueError("A notice must be a JSON object.")
    name, court = _plain(payload.get("name"), 300), _plain(payload.get("court"), 100)
    number = _plain(payload.get("registration_number"), 50)
    url = _plain(payload.get("official_url"), 1200)
    if (
        not name
        or not court
        or not number
        or not re.fullmatch(r"HR[AB]\s*\d{1,9}(?:\s?[A-Za-z]{1,4})?", number, re.I)
    ):
        raise ValueError(
            "Legal name, register court and a valid HRA/HRB number are required."
        )
    number = re.sub(r"\s+", "", number).upper()
    parts = urlsplit(url or "")
    if (
        parts.scheme != "https"
        or parts.netloc.lower() not in ("www.handelsregister.de", "handelsregister.de")
        or not parts.path.startswith("/rp_web/")
        or parts.fragment
        or "\\" in (url or "")
        or re.search(r"jsessionid|viewstate|sessionid|sec_ip", url or "", re.I)
    ):
        raise ValueError(
            "Supply a public HTTPS register-portal URL without session identifiers."
        )
    kind, quote = payload.get("event_type"), _plain(payload.get("quote"), 450)
    if not isinstance(kind, str) or kind not in NOTICE_TYPES or not quote:
        raise ValueError(
            "Supply a valid notice type and a short excerpt from the official document."
        )
    if payload.get("verified") is not True:
        raise ValueError("Confirm that you personally checked the official document.")
    dates = {}
    for field in ("registered_at", "published_at", "event_date"):
        date_value = payload.get(field)
        if date_value is not None:
            result = _day(date_value)
            if not result or result > _today():
                raise ValueError(
                    f"{field} must be a past or current ISO calendar date."
                )
        dates[field] = date_value
    if kind == "incorporation" and not dates["registered_at"]:
        raise ValueError(
            "An incorporation requires the explicit first registration date in the source."
        )
    if kind != "incorporation" and dates["registered_at"]:
        raise ValueError(
            "Only a first registration notice can set registered_at. Use event_date for later entries."
        )
    if (
        kind == "incorporation"
        and dates["event_date"]
        and dates["event_date"] != dates["registered_at"]
    ):
        raise ValueError(
            "Use the initial entry date as the event date for an incorporation."
        )
    return _legal(
        "german_register",
        "DE",
        name,
        number,
        dates["registered_at"],
        url,
        utcnow(),
        court=court,
        event_type=kind,
        published_at=dates["published_at"],
        event_date=dates["event_date"] or dates["registered_at"],
        quote=quote,
        excerpt_type="Analyst-transcribed notice",
        capture_mode="analyst_verified",
        summary=f"An analyst verified a German {kind} notice at {court}. Commercial progress requires separate evidence.",
    )


def recorded_registrations():
    """Read short, attributed primary-source observations collected during development."""
    data = json.loads(
        Path(__file__).with_name("uk_observations.json").read_text(encoding="utf-8")
    )
    rows = list(data["records"])
    norway_path = Path(__file__).with_name("norway_capture.json")
    if norway_path.is_file():
        scan = json.loads(norway_path.read_text(encoding="utf-8"))
        if scan.get("status") in ("success", "partial"):
            rows.extend(scan["records"])
    return rows


def to_record(legal):
    """Convert official legal events to the app schema. Eligibility for an investment remains open."""
    key = legal["source_key"]
    country = legal["country_code"]
    number = legal["registration_number"]
    registry = SOURCE_NAMES[key]
    observed = legal["first_observed_at"]
    registered = _day(legal.get("registered_at"))
    # German register numbers are scoped to a register court. Include the court in the stable identifier.
    register_number = (legal["court"] + " " + number) if legal.get("court") else number
    ident = hashlib.sha256(register_number.casefold().encode()).hexdigest()[:18]
    fresh = registered is not None and 0 <= (_today() - registered).days < 90
    initial = legal["event_type"] in ("incorporation", "initial_registration")
    signal = "INCORPORATION" if initial else "OTHER"
    event_date = legal.get("event_date") or (
        legal.get("registered_at") if initial else None
    )
    name = legal["name"]
    source_name = registry
    claim = (
        f"{registry} records the initial registration of {name} on {event_date}."
        if initial
        else (
            f"An analyst recorded a {legal['event_type']} notice from {legal['court']}."
        )
    )
    evidence = {
        "source_id": key,
        "source_name": source_name,
        "url": legal["official_url"],
        "title": name + " · " + registry,
        "quote": legal["quote"],
        "claim": claim,
        "signal_type": signal,
        "published_at": legal.get("published_at"),
        "event_date": event_date,
        "first_observed_at": observed,
        "retrieved_at": legal["retrieved_at"],
        "independence_group": key,
        "verification_status": "registry evidence",
        "extraction_method": legal["capture_mode"],
    }
    return {
        "id": f"reg-{country.lower()}-{ident}",
        "name": name,
        "kind": "prospect",
        "stage": "NEWLY_INCORPORATED" if initial and fresh else "UNKNOWN",
        "summary": legal["summary"],
        "sector": legal.get("sector") or "Unclassified",
        "country": country,
        "city": None,
        "university": None,
        "tags": list(legal.get("industry_codes", [])),
        "website": None,
        "funding_status": "UNKNOWN",
        "registration_status": "VERIFIED_REGISTERED",
        "registered_at": legal.get("registered_at"),
        "first_observed_at": observed,
        "team": [],
        "why_now": claim,
        "legal_entity": {
            **legal,
            "registry": registry,
            "registry_name": registry,
            "legal_name": name,
            "registration_number": register_number,
            "last_verified_at": legal["retrieved_at"],
        },
        "evidence": [evidence],
    }
