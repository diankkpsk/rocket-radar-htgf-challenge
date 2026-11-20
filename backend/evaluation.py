"""Read-only operating metrics for the current prospect feed."""

from collections import Counter
from statistics import median

from . import store
from .scoring import day


def _precision(ranked, k):
    top = ranked[:k]
    decisions = Counter(row["review_status"] for row in top)
    accepted, rejected = decisions["accept"], decisions["reject"]
    labelled = accepted + rejected
    if len(top) < k:
        reason = "insufficient_prospects"
    elif labelled < k:
        reason = "incomplete_labels"
    else:
        reason = "measured"
    return {
        "k": k,
        "available": len(top),
        "accepted": accepted,
        "rejected": rejected,
        "labelled": labelled,
        "unlabelled": len(top) - labelled,
        "value": accepted / k if reason == "measured" else None,
        "reason": reason,
        "ranked_ids": [row["id"] for row in top],
    }


def _signal_latency(rows):
    # A single article often produces multiple signals. Count each prospect/source URL once.
    urls = {}
    for row in rows:
        for evidence in row["evidence"]:
            key = (row["id"], evidence["url"])
            published = day(evidence.get("published_at"))
            observed = day(evidence.get("first_observed_at"))
            if key not in urls:
                urls[key] = (set(), set())
            dates, observations = urls[key]
            if published:
                dates.add(published)
            if observed:
                observations.add(observed)
    delays = []
    missing = conflicts = negative = 0
    for dates, observations in urls.values():
        if len(dates) > 1:
            conflicts += 1
        elif not dates or not observations:
            missing += 1
        else:
            delay = (min(observations) - next(iter(dates))).days
            if delay < 0:
                negative += 1
            else:
                delays.append(delay)
    return {
        "basis": "source publication to first observation, in calendar days",
        "unit": "prospect_source_url",
        "total": len(urls),
        "measured": len(delays),
        "missing_dates": missing,
        "conflicting_publication_dates": conflicts,
        "observed_before_publication": negative,
        "median_days": median(delays) if delays else None,
        "min_days": min(delays, default=None),
        "max_days": max(delays, default=None),
    }


def report(db):
    records = store.load(db)
    ranked = [row for row in records if row["kind"] == "prospect"]
    # Match the feed's descending priority and case-insensitive alphabetical tie break.
    ranked.sort(key=lambda row: (-row["scores"]["priority"], row["name"].casefold()))
    stages = Counter(row["stage"] for row in ranked)
    reviews = Counter(row["review_status"] for row in ranked)
    unresolved = sum(
        row["registration_status"] != "VERIFIED_REGISTERED" for row in ranked
    )
    duplicates = Counter(
        row[0]
        for row in db.execute("""
        SELECT d.decision FROM duplicate_review d
        JOIN ventures l ON l.id=d.left_id AND l.kind='prospect'
        JOIN ventures r ON r.id=d.right_id AND r.kind='prospect'
    """)
    )
    pairs = sum(duplicates.values())
    reviewed_pairs = duplicates["related"] + duplicates["distinct"]
    scans = list(
        db.execute("""
        SELECT mode, status, COUNT(*), SUM(discarded) FROM scans GROUP BY mode,status
    """)
    )
    live = {status: n for mode, status, n, _ in scans if mode == "live"}
    completed = sum(live.get(status, 0) for status in ("success", "partial", "failed"))
    return {
        "population": {
            "prospects": len(ranked),
            "portfolio_excluded": len(records) - len(ranked),
            "stage_counts": dict(stages),
            "unknown_stage": stages["UNKNOWN"],
            "unverified_registration": unresolved,
            "unknown_funding": sum(
                row["funding_status"] == "UNKNOWN" for row in ranked
            ),
            "review_counts": dict(reviews),
            "unlabelled": len(ranked) - reviews["accept"] - reviews["reject"],
        },
        "precision_at_5": _precision(ranked, 5),
        "precision_at_10": _precision(ranked, 10),
        "signal_latency": _signal_latency(ranked),
        "duplicates": {
            "flagged_pairs": pairs,
            "decision_counts": dict(duplicates),
            "reviewed_pairs": reviewed_pairs,
            "review_completion_rate": reviewed_pairs / pairs if pairs else None,
            "confirmed_entity_duplicate_rate": None,
        },
        "scan_health": {
            "live_status_counts": live,
            "completed_attempts": completed,
            "full_success_rate": live.get("success", 0) / completed
            if completed
            else None,
            "live_discarded_records": sum(
                d or 0 for mode, _, _, d in scans if mode == "live"
            ),
            "replay_runs": sum(n for mode, _, n, _ in scans if mode == "replay"),
            "parser_error_rate": None,
        },
        "unmeasured": [
            "source-wide recall",
            "competitive discovery lead time",
            "confirmed duplicate prevalence",
            "row-level parser error rate",
        ],
    }
