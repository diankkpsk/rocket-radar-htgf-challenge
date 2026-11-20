"""Evidence primitives shared by the public directory adapters."""

from datetime import datetime, timezone
import re
import unicodedata
from urllib.parse import urlsplit


def utc_now():
    return (
        datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    )


def slug(name):
    text = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def public_link(value):
    if not value or re.search(r"[\s<>]", value):
        return None
    try:
        parts = urlsplit(value)
        if (
            parts.scheme not in {"http", "https"}
            or not parts.hostname
            or "." not in parts.hostname
            or parts.username
            or parts.password
            or parts.port not in (None, 80, 443)
        ):
            return None
    except ValueError:
        return None
    return value


def excerpt(text, words=22):
    """Return a contiguous, visibly bounded excerpt without adding words."""
    return " ".join(text.split()[:words])


def evidence(
    source_id,
    source_name,
    url,
    title,
    quote,
    claim,
    signal_type,
    observed,
    published=None,
    event=None,
):
    return {
        "source_id": source_id,
        "source_name": source_name,
        "url": url,
        "title": title,
        "quote": quote,
        "claim": claim,
        "signal_type": signal_type,
        "published_at": published,
        "event_date": event,
        "first_observed_at": observed,
        "retrieved_at": observed,
    }


def record(key, name, kind="prospect", stage="POTENTIAL_PRE_COMPANY"):
    return {
        "id": key,
        "name": name,
        "kind": kind,
        "stage": stage,
        "summary": None,
        "sector": None,
        "country": None,
        "city": None,
        "university": None,
        "tags": [],
        "website": None,
        "funding_status": "UNKNOWN",
        "registration_status": "NOT_VERIFIED",
        "team": [],
        "evidence": [],
    }
