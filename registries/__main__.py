"""Local diagnostic and importer. Print structured results for inspection or ingestion."""

import argparse
import json
import sys
from pathlib import Path

from . import companies_house, coverage, import_estonia, norway, repository_search


def main():
    parser = argparse.ArgumentParser(
        description="FounderRadar official registry and technical-source tools"
    )
    group = parser.add_subparsers(dest="command", required=True)
    for name in ("uk", "norway", "estonia"):
        cmd = group.add_parser(name)
        cmd.add_argument("--days", type=int, choices=(7, 30, 90), default=30)
        cmd.add_argument(
            "--as-of", help="Last date in the inclusive window, YYYY-MM-DD"
        )
        if name == "estonia":
            cmd.add_argument(
                "path", type=Path, help="Local official basic data CSV or ZIP"
            )
            cmd.add_argument("--max-records", type=int, default=100)
            cmd.add_argument(
                "--previous",
                type=Path,
                help="Previous complete normalized scan of the same window",
            )
        else:
            cmd.add_argument("--page-size", type=int, default=20)
            cmd.add_argument("--cursor", type=int, default=0)
    group.add_parser("coverage").add_argument("query", nargs="?", default="")
    group.add_parser("github").add_argument("query")
    args = parser.parse_args()
    try:
        if args.command == "coverage":
            result = {"records": coverage(args.query)}
        elif args.command == "github":
            result = repository_search(args.query)
        elif args.command == "estonia":
            result = import_estonia(
                args.path,
                days=args.days,
                as_of=args.as_of,
                max_records=args.max_records,
            )
            if args.previous:
                if args.previous.stat().st_size > 4 * 1024**2:
                    raise ValueError("Previous scan exceeds 4 MiB.")
                previous = json.loads(args.previous.read_text(encoding="utf-8"))
                if (
                    previous.get("source_key") != "estonia"
                    or previous.get("status") != "success"
                    or previous.get("window") != result.get("window")
                ):
                    raise ValueError(
                        "Compare complete Estonia scans covering the same date window."
                    )
                old = {record["registration_number"] for record in previous["records"]}
                for record in result["records"]:
                    record["snapshot_first_appearance"] = (
                        record["registration_number"] not in old
                    )
        else:
            fn = companies_house if args.command == "uk" else norway
            result = fn(
                days=args.days,
                as_of=args.as_of,
                page_size=args.page_size,
                cursor=args.cursor,
            )
    except (ValueError, OSError, TypeError, KeyError) as e:
        parser.error(str(e))
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    print()
    return 1 if result.get("status") in ("failed", "credential_required") else 0


if __name__ == "__main__":
    sys.exit(main())
