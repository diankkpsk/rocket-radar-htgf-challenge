"""Back up and remove a local record, retaining a suppression key for future scans."""

import argparse
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend import store


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("id")
    parser.add_argument(
        "--restore-discovery",
        action="store_true",
        help="Remove suppression, allowing later scans to rediscover this ID.",
    )
    args = parser.parse_args()
    with store.connect() as db:
        if args.restore_discovery:
            db.execute("DELETE FROM metadata WHERE key=?", ("suppressed:" + args.id,))
            print("Future discovery enabled for this ID.")
            return
        row = db.execute("SELECT name FROM ventures WHERE id=?", (args.id,)).fetchone()
        if not row:
            parser.error("Candidate ID not present.")
        backup = store.dbpath().with_name(
            "removal-backup-" + store.now().replace(":", "-") + ".sqlite3"
        )
        target = sqlite3.connect(backup)
        try:
            db.backup(target)
        finally:
            target.close()
        db.execute(
            "INSERT OR REPLACE INTO metadata VALUES(?,?)",
            ("suppressed:" + args.id, store.now()),
        )
        db.execute("DELETE FROM search_index WHERE id=?", (args.id,))
        db.execute("DELETE FROM ventures WHERE id=?", (args.id,))
        db.execute(
            "DELETE FROM documents WHERE id NOT IN (SELECT document_id FROM evidence)"
        )
        db.execute(
            "DELETE FROM legal_entities WHERE id NOT IN (SELECT legal_id FROM legal_links)"
        )
        print(
            "Removed local record and suppressed rediscovery. Recoverable backup at",
            backup,
        )
    print(
        "Review packaged recordings, manual inbox entries and any exported reports before redistribution."
    )


if __name__ == "__main__":
    main()
