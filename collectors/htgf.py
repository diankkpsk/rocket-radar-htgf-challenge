"""Read HTGF's published English WordPress portfolio collection."""

import html
import json
from datetime import datetime
from urllib.parse import urlencode, urlsplit

from .common import evidence, excerpt, record, utc_now
from .dom import Tree
from .fetch import CollectionError

API = "https://www.htgf.de/wp-json/wp/v2/portfolio"
FIELDS = "id,link,title,date_gmt,modified_gmt,class_list,lang,slug,content"
LABELS = {
    "agritech-food": "Agritech & Food",
    "chemistry-industrial-biotech": "Chemistry & Industrial Biotech",
    "climate-tech": "Climate Tech",
    "deep-tech": "Deep Tech",
    "diagnostics-rd-tools": "Diagnostics & R&D Tools",
    "digital-health": "Digital Health",
    "digital-tech": "Digital Tech",
    "industrial-tech": "Industrial Tech",
    "medtech": "Medtech",
    "pharmaceuticals": "Pharmaceuticals",
}


def label(raw):
    return LABELS.get(raw, raw.replace("-und-", "-and-").replace("-", " ").capitalize())


def page_url(number):
    return (
        API
        + "?"
        + urlencode({"lang": "en", "per_page": 100, "page": number, "_fields": FIELDS})
    )


def parse_page(raw, observed):
    page = json.loads(raw) if isinstance(raw, str) else raw
    if not isinstance(page, list):
        raise CollectionError("Unexpected HTGF collection format")
    result = []
    for item in page:
        link = item.get("link", "")
        parts = urlsplit(link)
        if (
            item.get("lang") != "en"
            or not isinstance(item.get("id"), int)
            or parts.scheme != "https"
            or parts.netloc != "www.htgf.de"
            or not parts.path.startswith("/en/portfolio/")
            or "portfolio" not in item.get("class_list", [])
        ):
            raise CollectionError(
                "Unexpected entry in the English HTGF portfolio collection"
            )
        name = html.unescape(item["title"]["rendered"]).strip()
        if not name:
            raise CollectionError("HTGF entry lacks a company name")
        classes = item["class_list"]

        def values(prefix):
            return [
                label(t.removeprefix(prefix)) for t in classes if t.startswith(prefix)
            ]

        sectors, foci, older = (
            values("sectors-"),
            values("focus_areas-"),
            values("branchen22-"),
        )
        primary = sectors or older
        r = record("htgf-" + str(item["id"]), name, kind="portfolio", stage="UNKNOWN")
        r.update(
            sector=primary[0] if primary else None,
            tags=list(dict.fromkeys(sectors + foci + older)),
            funding_status="UNKNOWN",
        )
        description = Tree((item.get("content") or {}).get("rendered") or "").root
        paragraph = next(
            (
                n.text()
                for n in description.walk()
                if n.tag == "p" and len(n.text()) > 40
            ),
            "",
        )
        r["summary"] = (
            excerpt(paragraph) + ("…" if len(paragraph.split()) > 22 else "")
            if paragraph
            else "HTGF lists "
            + name
            + " in its investment portfolio."
            + (
                " Its index classifies the company under " + ", ".join(primary) + "."
                if primary
                else ""
            )
        )
        published = item.get("date_gmt")
        if published:
            try:
                published = datetime.fromisoformat(published).strftime(
                    "%Y-%m-%dT%H:%M:%SZ"
                )
            except (TypeError, ValueError) as exc:
                raise CollectionError("Invalid HTGF listing timestamp") from exc
        entry = evidence(
            "htgf",
            "High-Tech Gründerfonds",
            link,
            name,
            excerpt(paragraph) if paragraph else name,
            "The publisher's English portfolio includes this company.",
            "PORTFOLIO_MEMBERSHIP",
            observed,
            published,
        )
        r["evidence"].append(entry)
        result.append(r)
    return result


def collect(fetcher):
    records = []
    ids = set()
    for number in range(1, 21):
        # WordPress sends this specific structured error for a page past an exact
        # multiple of 100. Other 400 responses remain visible failures.
        try:
            raw = fetcher.get(page_url(number))
        except CollectionError as exc:
            if (
                number > 1
                and getattr(exc, "code", "") == "rest_post_invalid_page_number"
            ):
                return records
            raise
        page = parse_page(raw, utc_now())
        keys = {r["id"] for r in page}
        if len(keys) != len(page) or keys & ids:
            raise CollectionError(
                "Overlapping HTGF pages. Retry the scan against a stable index."
            )
        ids.update(keys)
        records.extend(page)
        if len(page) < 100:
            if not records:
                raise CollectionError("The HTGF portfolio index returned no entries")
            return records
    raise CollectionError("HTGF index exceeded the 2,000-entry scan limit")
