import csv
import io
import re


def csv_cell(value):
    s = "" if value is None else str(value)
    return (
        "'" + s
        if s.lstrip().startswith(("=", "+", "-", "@"))
        or s.startswith(("\t", "\r", "\n"))
        else s
    )


def table(records):
    out = io.StringIO(newline="")
    writer = csv.writer(out)
    writer.writerow(
        [
            "Name",
            "Collection",
            "Stage",
            "Country",
            "Sector",
            "Quality",
            "Confidence",
            "Priority",
            "Registration",
            "Registered at",
            "Funding",
            "First observed",
            "Signal date",
            "Primary source",
            "Evidence excerpt",
            "Watched",
            "Analyst note",
        ]
    )
    for r in records:
        e = r["evidence"][0]
        writer.writerow(
            [
                csv_cell(v)
                for v in (
                    r["name"],
                    r["kind"],
                    r["stage"],
                    r["country"],
                    r["sector"],
                    r["scores"]["quality"],
                    r["scores"]["confidence"],
                    r["scores"]["priority"],
                    r["registration_status"],
                    r["registered_at"],
                    r["funding_status"],
                    r["first_observed_at"],
                    r["last_signal_at"],
                    e["url"],
                    e["quote"],
                    r["watched"],
                    r["note"],
                )
            ]
        )
    return out.getvalue()


def plain(value):
    return (
        re.sub(r"([\\`*_{}\[\]()<>#!|])", r"\\\1", str(value or "Unknown"))
        .replace("\r", " ")
        .replace("\n", " ")
    )


def memo(r):
    lines = [
        f"# {plain(r['name'])}",
        "",
        plain(r["summary"]),
        "",
        f"- Collection: {r['kind']}",
        f"- Stage: {r['stage']}",
        f"- Sector: {plain(r['sector'])}",
        f"- Country: {plain(r['country'])}",
        f"- Registration: {r['registration_status']}",
        f"- Verified incorporation date: {plain(r['registered_at'])}",
        f"- Funding: {r['funding_status']}",
        f"- First observed by FounderRadar: {r['first_observed_at']}",
        f"- Quality: {r['scores']['quality']}/100. Evidence confidence: {r['scores']['confidence']}/100.",
        "",
        "## Why investigate",
        "",
        plain(r["why_now"]),
    ]
    if r.get("best_find"):
        lines += [
            "",
            plain(r["best_find"]["rationale"]),
            "",
            "### Next verification",
            "",
            plain(r["best_find"]["next_check"]),
        ]
    lines += ["", "## Team", ""]
    for p in r["team"]:
        lines += [
            f"- {plain(p['name'])}, {plain(p.get('role'))}. <{p.get('source_url')}>"
        ]
    if not r["team"]:
        lines += ["No founding team verified in the stored evidence."]
    lines += ["", "## Evidence", ""]
    for e in r["evidence"]:
        lines += [
            f"### {plain(e['source_name'])} · {plain(e.get('title'))}",
            "",
            plain(e.get("claim")),
            "",
            f"> {plain(e.get('quote'))}",
            "",
            f"Source: <{e['url']}>",
            f"Published: {e['published_at'] or 'unknown'}. Event: {e['event_date'] or 'unknown'}. Observed: {e['first_observed_at']}. Retrieved: {e['retrieved_at']}.",
            "",
        ]
    lines += [
        "## Open questions",
        "",
        "Competitive database listing dates have not been verified.",
    ]
    if r.get("note"):
        lines += ["", "## Analyst note", "", plain(r["note"])]
    return "\n".join(lines) + "\n"
