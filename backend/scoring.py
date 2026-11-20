"""Deterministic, evidence-linked qualification. Weights are analyst heuristics."""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime, timezone
from urllib.parse import urlsplit


def normalized(value):
    text = unicodedata.normalize("NFKD", str(value or "").casefold())
    return " ".join("".join(c for c in text if not unicodedata.combining(c)).split())


def day(value):
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except (ValueError, TypeError):
        return None


def independence(e):
    host = (urlsplit(e["url"]).hostname or "").removeprefix("www.")
    return str(e.get("independence_group") or host)


def independent_groups(evidence):
    # One publisher or a mirrored verbatim excerpt supplies one corroboration group.
    groups = []
    for e in evidence:
        keys = {"publisher:" + independence(e)}
        quote = normalized(e.get("quote"))
        if len(quote) >= 40:
            keys.add("text:" + quote)
        overlapping = [g for g in groups if g & keys]
        for group in overlapping:
            keys |= group
            groups.remove(group)
        groups.append(keys)
    return len(groups)


NEGATIVE = {
    "NOT_A_STARTUP": r"course assignment|class assignment|student homework|lab exercise|hackathon.only|personal hobby|web.design agency|freelance agency|consultancy services only",
    "RESEARCH_ONLY": r"research.only|academic exercise|research project without commercial",
}
EARLY = {
    "COMMERCIAL_RESEARCH",
    "STARTUP_PROGRAMME",
    "UNIVERSITY_GRANT",
    "EXIST_GRANT",
    "COFOUNDER_SEARCH",
    "ACCELERATOR_ACCEPTANCE",
    "PILOT_CUSTOMERS",
    "PROTOTYPE",
    "BETA_TEST",
    "STARTUP_AWARD",
    "COMPETITION_FINALIST",
    "CUSTOMER_DISCOVERY",
}
PRODUCT = {
    "PROTOTYPE",
    "AI_DEMO",
    "MARKET_LAUNCH",
    "BETA_TEST",
    "PATENT_COMMERCIALIZATION",
    "GITHUB_RELEASE",
}
DEMAND = {"PILOT_CUSTOMERS", "BETA_TEST", "CUSTOMER_DISCOVERY", "MARKET_LAUNCH"}
CUES = {
    "pilot": r"letter[s]? of intent|customer interview|pilot customer|pilot project|pilotkunden|design partner|paying customer",
    "proto": r"prototype|demonstrator|patent|field.test|proof.of.concept|prototyp|demonstrated",
    "rd": r"technology|technologie|spin.off|spinout|research|entwickel|develop|method|platform|sensor|recycl|automati[cz]|material|algorithm",
    "commerce": r"commercial|customer|market|product|entrepreneur|pilot|industrie|industrial|startup|start.up|gründung|spin.off",
}


def assess(record, today=None):
    today = today or datetime.now(timezone.utc).date()
    es = record.get("evidence", [])
    texts = {e["id"]: normalized(e.get("quote")) for e in es}
    by_type = lambda types: [e for e in es if e.get("signal_type") in types]

    def cue(key):
        return [e for e in es if re.search(CUES[key], texts[e["id"]])]

    stage = record.get("stage", "UNKNOWN")
    flags = []
    for flag, expression in NEGATIVE.items():
        if any(re.search(expression, t) for t in texts.values()):
            flags.append(flag)
    if record["kind"] == "portfolio":
        stage = "UNKNOWN"
    elif flags:
        stage = flags[0]
    elif stage == "POTENTIAL_PRE_COMPANY" and not (by_type(EARLY) or cue("commerce")):
        stage = "UNKNOWN"
    elif stage == "NEWLY_INCORPORATED":
        reg = day(record.get("registered_at"))
        if not (
            record.get("legal_entity")
            and record.get("registration_status") == "VERIFIED_REGISTERED"
            and reg
            and 0 <= (today - reg).days < 90
            and by_type({"INCORPORATION"})
        ):
            stage = "UNKNOWN"
    record["stage"] = stage
    eligible = record["kind"] == "prospect" and not flags
    breakdown = []

    def part(label, maximum, points, reason, items):
        # A positive score can only cite evidence actually present on this record.
        ids = list(dict.fromkeys(e["id"] for e in items))
        value = points if ids and eligible else 0
        breakdown.append(
            {
                "label": label,
                "max": maximum,
                "score": value,
                "reason": reason
                if value
                else "No qualifying evidence in this category.",
                "evidence_ids": ids if value else [],
            }
        )

    demand = by_type(DEMAND) or cue("pilot")
    commercial = cue("commerce") or by_type(
        {
            "COMMERCIAL_RESEARCH",
            "EXIST_GRANT",
            "STARTUP_PROGRAMME",
            "ACCELERATOR_ACCEPTANCE",
        }
    )
    part(
        "Commercial intent",
        25,
        25 if demand else 12,
        "Cited customer, pilot or launch signal."
        if demand
        else "A source describes commercialization or programme participation.",
        demand or commercial,
    )
    team_links = {p.get("source_url") for p in record.get("team", []) if p.get("name")}
    team = [e for e in es if e["url"] in team_links]
    formation = by_type({"COFOUNDER_SEARCH", "TEAM_FORMATION"})
    part(
        "Founding team",
        20,
        20 if team and len(record.get("team", [])) >= 2 else 12 if team else 7,
        "A cited professional source identifies the team."
        if team
        else "Explicit team formation signal.",
        team or formation,
    )
    proto = by_type(PRODUCT) or cue("proto")
    part(
        "Technology",
        20,
        20 if proto else 10,
        "Cited prototype, release or IP evidence."
        if proto
        else "The source describes technical development.",
        proto or cue("rd"),
    )
    early = (by_type(EARLY) or commercial) if stage == "POTENTIAL_PRE_COMPANY" else []
    if stage == "NEWLY_INCORPORATED":
        early = by_type({"INCORPORATION"})
    part(
        "Earliness",
        20,
        18 if stage == "POTENTIAL_PRE_COMPANY" else 8,
        "Early commercial formation signal."
        if stage == "POTENTIAL_PRE_COMPANY"
        else "Verified recent formation date.",
        early,
    )
    known = [
        (e, day(e.get("event_date")) or day(e.get("published_at")))
        for e in es
        if e.get("signal_type")
        not in {None, "OTHER", "PORTFOLIO_LISTING", "INCORPORATION"}
    ]
    recent = [e for e, d in known if d and 0 <= (today - d).days <= 180]
    part(
        "Momentum",
        15,
        15 if len(recent) > 1 and independent_groups(recent) > 1 else 8,
        "Dated non-registry milestone within the past 180 days.",
        recent,
    )
    independence_count = independent_groups(es)
    dated = [e for e in es if day(e.get("published_at")) or day(e.get("event_date"))]
    has_legal = bool(record.get("legal_entity") and record.get("registered_at"))
    confidence = min(
        100,
        (25 if es else 0)
        + min(30, 15 * independence_count)
        + (15 if dated else 0)
        + (10 if team else 0)
        + (15 if has_legal else 0)
        + (5 if any(e.get("quote") for e in es) else 0),
    )
    quality_raw = sum(p["score"] for p in breakdown)
    ceiling = 45 if independence_count <= 1 and not (proto or demand or team) else 100
    quality = min(quality_raw, ceiling)
    focus = 3 if record.get("country") == "DE" else 0
    priority = (
        round(0.68 * quality + 0.22 * confidence + (7 if recent else 0) + focus)
        if eligible
        else 0
    )
    record["scores"] = {
        "quality": quality,
        "confidence": confidence,
        "earliness": breakdown[3]["score"],
        "momentum": breakdown[4]["score"],
        "priority": priority,
        "breakdown": breakdown,
        "ceiling": ceiling,
        "quality_before_ceiling": quality_raw,
        "confidence_reason": f"{independence_count} independent source group(s); {len(dated)} dated evidence item(s). "
        + (
            "Official registry identifier verified."
            if has_legal
            else "No verified registry identifier."
        ),
        "priority_reason": "68% quality + 22% confidence + 7 for a recent milestone + 3 for Germany.",
    }
    record["flags"] = flags
    record["independent_sources"] = independence_count
    record["evidence_count"] = len(es)
    signal_dates = [
        e.get("event_date") or e.get("published_at")
        for e in es
        if e.get("event_date") or e.get("published_at")
    ]
    record["last_signal_at"] = max(signal_dates, default=None)
    record["earliest_signal_at"] = min(signal_dates, default=None)
    record["comparison_status"] = "unknown"
    record["why_now"] = (
        (demand[0].get("claim") if demand else None)
        or (recent[0].get("claim") if recent else None)
        or (es[0].get("claim") if es else None)
        or "Timing needs verification."
    )
    return record
