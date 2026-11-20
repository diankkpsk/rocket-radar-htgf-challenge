"""Bounded public repository discovery for manual cross-source verification."""

import os
import re
from urllib.parse import urlsplit

from .net import SourceError, fetch, utcnow
from .official import _batch, _fail, _limit


def repository_search(query, *, page=1, page_size=10, transport=fetch):
    if (
        not isinstance(query, str)
        or not 2 <= len(query.strip()) <= 180
        or any(ord(c) < 32 for c in query)
    ):
        raise ValueError("Supply a public repository query of 2 to 180 characters.")
    _limit(page, 1, 3, "Page")
    _limit(page_size, 1, 20, "Page size")
    if re.search(
        r"\bis\s*:\s*(private|internal)|\bvisibility\s*:\s*(private|internal)",
        query,
        re.I,
    ):
        raise ValueError("Only public repositories are supported.")
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = "Bearer " + token
    q = query.strip() + " is:public fork:false archived:false"
    b = _batch("github")
    b["requests"] = 1
    try:
        resp = transport(
            "github", {"q": q, "page": page, "per_page": page_size}, headers
        )
    except SourceError as err:
        return _fail(b, err)
    rows = resp.get("items")
    if not isinstance(rows, list) or len(rows) > page_size:
        return _fail(b, "Unexpected GitHub search result schema.")
    now = utcnow()
    b["retrieved_at"] = now
    for row in rows:
        b["records_parsed"] += 1
        if (
            not isinstance(row, dict)
            or row.get("private") is not False
            or row.get("visibility", "public") != "public"
        ):
            continue
        full = row.get("full_name", "")
        if not isinstance(full, str) or not re.fullmatch(
            r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", full
        ):
            continue
        url = f"https://github.com/{full}"
        if (
            row.get("html_url") != url
            or row.get("fork") is True
            or row.get("archived") is True
        ):
            continue
        owner = row.get("owner") or {}
        license_obj = row.get("license") or {}
        homepage = row.get("homepage")
        homepage_parts = None
        if isinstance(homepage, str):
            try:
                homepage_parts = urlsplit(homepage)
            except ValueError:
                pass
        if (
            not homepage_parts
            or homepage_parts.scheme != "https"
            or not homepage_parts.hostname
            or homepage_parts.username
            or homepage_parts.password
        ):
            homepage = None
        b["records"].append(
            {
                "source_key": "github",
                "repo": full,
                "url": url,
                "description": str(row.get("description") or "")[:600],
                "organization": owner.get("login")
                if isinstance(owner, dict) and owner.get("type") == "Organization"
                else None,
                "homepage": homepage,
                "license": license_obj.get("spdx_id")
                if isinstance(license_obj, dict)
                else None,
                "created_at": row.get("created_at"),
                "pushed_at": row.get("pushed_at"),
                "topics": [t for t in row.get("topics", []) if isinstance(t, str)][:20],
                "stars": row.get("stargazers_count"),
                "retrieved_at": now,
                "verification_status": "unlinked technical signal; match independently before attaching to a venture",
            }
        )
    b["discarded"] = {"ineligible_or_malformed": len(rows) - len(b["records"])}
    if resp.get("incomplete_results") is True:
        b["status"] = "partial"
        b["errors"].append("GitHub marked these search results incomplete.")
    total = resp.get("total_count", 0)
    if isinstance(total, int) and page * page_size < total and page < 3:
        b["next_cursor"] = page + 1
    return b
