"""Rebuild the export from the original capture directory for provenance audits.

Usage from the application directory: python3 -m collectors.build_capture SOURCE_DIRECTORY
Original web responses stay local to the person running the collection. The
distributed package includes the parsed data and a hash manifest.
"""

import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from . import htgf, kit, tum
from .common import evidence, excerpt, public_link
from .dom import Tree
from .reviewed import REVIEWS, apply

DATA = REVIEWS.parent


def stamp(value):
    return (
        datetime.fromisoformat(value.replace("Z", "+00:00"))
        .astimezone(timezone.utc)
        .isoformat(timespec="seconds")
        .replace("+00:00", "Z")
    )


def save(path, rows):
    path.write_text(
        json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def build(folder):
    documents = []

    def read(filename, url, observed):
        contents = (folder / filename).read_bytes()
        documents.append(
            {
                "file": filename,
                "url": url,
                "retrieved_at": observed,
                "sha256": hashlib.sha256(contents).hexdigest(),
                "bytes": len(contents),
            }
        )
        return contents.decode("utf-8")

    times = {}
    for filename in ("additional.log", "bay.log"):
        for line in (folder / filename).read_text().splitlines():
            key, ts, _, url = line.split()
            times[key] = stamp(ts), url
    t = "2026-11-20T14:17:36Z"
    records = tum.parse(read("tum.html", tum.URL, t), t)
    kit_index_stamp = stamp(
        re.search(r"KIT captured (\S+)", (folder / "capture.log").read_text())[1]
    )
    profile_links = kit.index(read("kit.html", kit.URL, kit_index_stamp))
    for link in profile_links:
        suffix = link.rstrip("/").rsplit("founder-of-the-month-", 1)[-1]
        key = "kit-" + suffix
        if suffix == "onsite-solutions":
            filename = "kit-detail.html"
            ts = "2026-11-20T14:22:21Z"
        else:
            filename = key + ".html"
            ts, logged_url = times[key]
            assert logged_url == link
        records.append(kit.parse(read(filename, link, ts), link, ts))
    early = {}
    for page, expected, instant in re.findall(
        r"HTGF (\d+) (\d+) (\S+)", (folder / "capture.log").read_text()
    ):
        ts = stamp(instant)
        url = htgf.page_url(int(page)).removesuffix("%2Ccontent")
        rows = htgf.parse_page(read("htgf-wp-" + page + ".json", url, ts), ts)
        assert len(rows) == int(expected)
        early.update({r["id"]: ts for r in rows})
    for page, expected, instant in re.findall(
        r"HTGF (\d+) (\d+) (\S+)", (folder / "rich.log").read_text()
    ):
        ts = stamp(instant)
        rows = htgf.parse_page(
            read("htgf-rich-" + page + ".json", htgf.page_url(int(page)), ts), ts
        )
        assert len(rows) == int(expected)
        for row in rows:
            # Earlier listing-only response establishes membership for exactly
            # the same observation; descriptive segments first appeared later.
            for e in row["evidence"]:
                if e["quote"] == row["name"] and row["id"] in early:
                    e["first_observed_at"] = early[row["id"]]
        records.extend(rows)

    selected = next(r for r in records if r["name"] == "IsoSphere Technologies")
    brief = {
        "rationale": "IsoSphere pairs a specific research-supply problem with early buyer conversations. Its TUM profile reports over 60 customer interviews and 14 letters of intent. An interview names both founders, and MIT's prize programme independently lists the team. The partner identities, order values and conversion of those letters into paid work remain unverified.",
        "next_check": "Ask the team how many letters of intent have converted to paid pilots, confirm production readiness and pricing, and verify incorporation and prior equity financing with primary records.",
    }
    fields = {"city": "Garching", "country": "DE", "best_find": brief}
    reviews = {
        selected["id"]: {"name": selected["name"], "fields": fields, "evidence": []}
    }
    supplemental = [
        (
            "chem",
            "chemanager",
            "CHEManager",
            "IsoSphere Technologies: FLTMC Finalist Profile",
            "Co-Founders Alba Impelmann (CEO) and Mark Deeprose (CTO)",
            "The founder interview identifies Alba Impelmann as CEO and Mark Deeprose as CTO.",
            "TEAM_FORMATION",
            "2026-06-01",
        ),
        (
            "mit",
            "mit_cep",
            "MIT Climate & Energy Prize",
            "Meet the 2026 MIT CEP Winners!",
            "$5k Munich Semi-fininalist: IsoSphere Technologies",
            "The organiser lists IsoSphere for the $5,000 Munich semifinal prize.",
            "STARTUP_AWARD",
            None,
        ),
        (
            "bay",
            "baystartup",
            "BayStartUP",
            "Acht Startups im Finale des Münchner Businessplan Wettbewerbs 2026",
            "IsoSphere Technologies aus Garching",
            "BayStartUP lists the Garching team as a Munich Business Plan Competition finalist.",
            "COMPETITION_FINALIST",
            "2026-07-29",
        ),
    ]
    prior_brief = read("best.txt", None, "2026-11-20T14:17:42Z")
    for key, sid, publisher, title, quote, claim, signal, date in supplemental:
        ts, url = times[key]
        markup = Tree(read(key + ".html", url, ts)).root.text()
        assert quote in markup and title in markup, key
        if date:
            assert datetime.fromisoformat(date).strftime("%d.%m.%Y") in markup, key
        item = evidence(sid, publisher, url, title, quote, claim, signal, ts, date)
        if quote in prior_brief and url in prior_brief:
            item["first_observed_at"] = "2026-11-20T14:17:42Z"
        reviews[selected["id"]]["evidence"].append(item)
    fields["team"] = [
        {"name": n, "role": role, "source_url": times["chem"][1]}
        for n, role in [
            ("Alba Impelmann", "Co-founder & CEO"),
            ("Mark Deeprose", "Co-founder & CTO"),
        ]
    ]

    # Earlier profile captures are publisher-rendered pages, including the official
    # Markdown representation. Split at each source header, including adjoining articles.
    path = folder / "htgf_profiles.txt"
    profile_text = path.read_text()
    sections = re.split(
        r"(?m)(?=^[^\n]{0,200}\(https://www\.htgf\.de/[^\n)]+\)\ncite)", profile_text
    )
    by_path = {
        urlsplit(r["evidence"][0]["url"]).path: r
        for r in records
        if r["kind"] == "portfolio"
    }
    used = set()
    for section in sections:
        header = re.match(
            r"[^\n]*\((https://www\.htgf\.de/en/portfolio/htgffamily/[^)]+)\)\n",
            section,
        )
        if not header:
            continue
        url = header[1]
        r = by_path.get(urlsplit(url).path)
        if not r or url in used:
            continue
        used.add(url)
        lines = [
            m[1].strip()
            for m in re.finditer(
                r"(?m)^L\d+: ?(.*)$",
                section.split(
                    "--------------------------------------------------------------------------------"
                )[0],
            )
        ]

        def next_paragraph(label):
            for i, line in enumerate(lines):
                if " ".join(line.split()) in label:
                    return next((l for l in lines[i + 1 :] if l), "")
            return ""

        paragraph = next_paragraph({"## Beschreibungstext", "## About the company"})
        if not paragraph or paragraph.startswith(("#", "【")) or len(paragraph) < 10:
            continue
        short = excerpt(paragraph, 20)
        f = {"summary": short + ("…" if len(paragraph.split()) > 20 else "")}
        web = next_paragraph({"## Unternehmenswebsite"})
        link = re.search(r"\]\((https?://[^)]+)\)", web)
        candidate = (
            link[1] if link else ("https://" + web if web.startswith("www.") else web)
        )
        if public_link(candidate):
            f["website"] = candidate
        ts = "2026-11-20T14:17:42Z"
        item = evidence(
            "htgf",
            "High-Tech Gründerfonds",
            url,
            r["name"],
            short,
            "The HTGF company profile describes this portfolio business.",
            "PORTFOLIO_PROFILE",
            ts,
        )
        reviews[r["id"]] = {"name": r["name"], "fields": f, "evidence": [item]}
    documents.append(
        {
            "file": path.name,
            "retrieved_at": "2026-11-20T14:17:42Z",
            "kind": "Archived public profile readings",
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "bytes": path.stat().st_size,
        }
    )
    save(REVIEWS, reviews)
    save(DATA / "records.json", apply(records))
    save(DATA / "capture_manifest.json", documents)


if __name__ == "__main__":
    build(Path(sys.argv[1]))
