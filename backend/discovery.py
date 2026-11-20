"""Multilingual query previews and optional, transient Brave Web Search results."""

from __future__ import annotations

import html
import http.client
import json
import math
import os
import re
import threading
import time
from urllib.parse import urlencode

from registries import coverage, net

from .store import ROOT, web_url


COUNTRIES = {row["country_code"]: row["country"] for row in coverage()}
INTENT = json.loads((ROOT / "config" / "intent.json").read_text(encoding="utf-8"))
LANGUAGES = {
    "AT": "de",
    "BE": "nl",
    "CH": "de",
    "DE": "de",
    "ES": "es",
    "FR": "fr",
    "GB": "en",
    "IE": "en",
    "IT": "it",
    "NL": "nl",
    "PL": "pl",
}
GERMANY = dict(
    en="Germany",
    de="Deutschland",
    fr="Allemagne",
    it="Germania",
    es="Alemania",
    nl="Duitsland",
    pl="Niemcy",
)
# Other directory countries use a worldwide search with a country name in the query.
BRAVE_REGIONS = set("ALL AT BE CH DE DK ES FI FR GB IT NL NO PL PT RU SE TR".split())
MANUAL = "/api/v1/import-url"
MAX_PLAN = 42
RESULT_COUNT = 5
_rate_lock = threading.Lock()
_next_request = 0.0


def _country(value):
    if value is not None and not isinstance(value, str):
        raise ValueError("Choose a country from the coverage directory or ALL.")
    code = (value or "").strip().upper() or "ALL"
    if code != "ALL" and code not in COUNTRIES:
        raise ValueError("Choose a country from the coverage directory or ALL.")
    return code


def _text(value, max_chars, label):
    if (
        not isinstance(value, str)
        or len(value) > max_chars
        or any(not c.isprintable() for c in value)
    ):
        raise ValueError(
            f"{label} must be printable text up to {max_chars} characters."
        )
    return " ".join(value.split())


def plan(country="DE", technology="", limit=14):
    code = _country(country)
    technology = _text(technology, 100, "Technology")
    if len(technology.split()) > 24:
        raise ValueError("Use up to 24 words for a project or technology.")
    if type(limit) is not int or not 1 <= limit <= MAX_PLAN:
        raise ValueError(f"Preview between 1 and {MAX_PLAN} queries.")
    languages = sorted(
        INTENT, key=lambda lang: (lang != LANGUAGES.get(code, "en"), lang != "en")
    )
    site = {"ALL": "github.com", "GB": "uk", "XK": "github.com"}.get(code, code.lower())
    items = []
    for round_index in range((limit + len(languages) - 1) // len(languages)):
        for index, lang in enumerate(languages):
            phrases = INTENT[lang]
            phrase = phrases[round_index % len(phrases)]
            words = [f'"{phrase}"', technology]
            site_scope = (index + round_index) % 2 == 1
            if site_scope:
                words.append(f"site:{site}")
                if code == "XK":
                    words.append(COUNTRIES[code])
            elif code == "DE":
                words.append(GERMANY[lang])
            elif code != "ALL":
                words.append(COUNTRIES[code])
            words.append(f"lang:{lang}")
            scope = "site" if site_scope else ("web" if code == "ALL" else "country")
            items.append(
                {
                    "language": lang,
                    "scope": scope,
                    "query": " ".join(filter(None, words)),
                }
            )
            if len(items) == limit:
                break
    return {
        "country": code,
        "technology": technology,
        "items": items,
        "configured": bool(os.getenv("BRAVE_SEARCH_API_KEY", "").strip()),
        "manual_intake": MANUAL,
    }


def _response(status, message, items=None, **extra):
    return {
        "status": status,
        "message": message,
        "items": items or [],
        "manual_intake": MANUAL,
        **extra,
    }


def _result_items(payload):
    web = payload.get("web", {})
    if not isinstance(web, dict) or not isinstance(web.get("results", []), list):
        raise net.SourceError("Unexpected web results.")
    items, seen = [], set()
    for row in web.get("results", [])[:RESULT_COUNT]:
        if not isinstance(row, dict):
            continue
        try:
            url = web_url(row.get("url"))
        except ValueError:
            continue
        if url in seen:
            continue
        seen.add(url)
        item = {"url": url}
        for key, bound in (("title", 250), ("description", 450)):
            value = row.get(key)
            item[key] = (
                " ".join(html.unescape(value).split())[:bound]
                if isinstance(value, str)
                else ""
            )
        items.append(item)
    return items


def web_search(query, country="DE"):
    global _next_request
    code = _country(country)
    query = _text(query, 300, "Query")
    if not query or len(query.split()) > 40:
        raise ValueError("Enter a search query of 1 to 40 words.")
    key = os.getenv("BRAVE_SEARCH_API_KEY", "").strip()
    if not key:
        return _response(
            "credential_required",
            "Set BRAVE_SEARCH_API_KEY to search, or submit a publisher URL for manual review.",
        )
    if not key.isascii() or not key.isprintable():
        return _response(
            "credential_required", "Check the configured Brave Search API key."
        )
    region = code if code in BRAVE_REGIONS else "ALL"
    if (
        code != "ALL"
        and region == "ALL"
        and COUNTRIES[code].casefold() not in query.casefold()
    ):
        query += ' "' + COUNTRIES[code] + '"'
    params = {
        "q": query,
        "country": region,
        "count": RESULT_COUNT,
        "result_filter": "web",
        "spellcheck": "false",
        "text_decorations": "false",
        "safesearch": "moderate",
    }
    language = re.search(r"(?:^|\s)lang:([a-z]{2})(?:\s|$)", query)
    if language and language[1] in INTENT:
        params["search_lang"] = language[1]
    headers = {
        "X-Subscription-Token": key,
        "Accept": "application/json",
        "Accept-Encoding": "identity",
        "User-Agent": "FounderRadar/1.0",
    }
    with _rate_lock:
        remaining = _next_request - time.monotonic()
        if remaining > 0:
            return _response(
                "rate_limited",
                "Wait before running another search.",
                retry_after=math.ceil(remaining),
            )
        _next_request = time.monotonic() + 1
    try:
        # The shared transport pins a checked public address and verifies TLS. No result URL is fetched.
        payload = net._request(
            "api.search.brave.com", "/res/v1/web/search?" + urlencode(params), headers
        )
        return _response(
            "ok",
            "Open a publisher page to verify any signal you want to save.",
            _result_items(payload),
        )
    except net.SourceError as exc:
        if exc.status == 429 or exc.retry_after is not None:
            delay = max(1, exc.retry_after if exc.retry_after is not None else 60)
            with _rate_lock:
                _next_request = max(_next_request, time.monotonic() + delay)
            return _response(
                "rate_limited", "The provider requested a pause.", retry_after=delay
            )
        if exc.status in (401, 403):
            return _response(
                "credential_required",
                "Check the API key and its Web Search subscription.",
            )
    except (OSError, http.client.HTTPException):
        pass
    return _response(
        "unavailable",
        "The search provider could not return results. You can submit a publisher URL for manual review.",
    )
