"""Attach dated, manually verified signals without issuing a new retrieval claim."""

import json
from pathlib import Path

REVIEWS = Path(__file__).resolve().parents[1] / "data" / "reviewed.json"


def apply(records):
    items = json.loads(REVIEWS.read_text(encoding="utf-8"))
    for row in records:
        review = items.get(row["id"])
        if review and review["name"] == row["name"]:
            row.update(review["fields"])
            for item in review["evidence"]:
                identity = (
                    item["source_id"],
                    item["url"],
                    item["signal_type"],
                    item["quote"],
                )
                if not any(
                    (e["source_id"], e["url"], e["signal_type"], e["quote"]) == identity
                    for e in row["evidence"]
                ):
                    row["evidence"].append(item)
    return records
