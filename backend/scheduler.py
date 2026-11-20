"""Single local schedule client; the API reserves jobs atomically."""

import json
import time
from datetime import datetime, timezone, timedelta
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


def serve(port):
    base = f"http://127.0.0.1:{port}/api/v1"

    def request(path, payload=None):
        headers = {"Content-Type": "application/json"} if payload else {}
        req = Request(
            base + path,
            headers=headers,
            data=json.dumps(payload).encode() if payload else None,
        )
        with urlopen(req, timeout=8) as res:
            return json.load(res)

    while True:
        try:
            conf = request("/settings")
            if conf["scheduled"]:
                for src in request("/sources")["items"]:
                    if not src["enabled"] or not src["can_scan"]:
                        continue
                    last = src["last_attempt_at"]
                    since = (
                        datetime.fromisoformat(last.replace("Z", "+00:00"))
                        if last
                        else None
                    )
                    if since and datetime.now(timezone.utc) - since < timedelta(
                        hours=conf["interval_hours"]
                    ):
                        continue
                    job = request("/scans", {"source_id": src["id"], "mode": "live"})
                    while request("/scans/" + job["id"])["status"] == "running":
                        time.sleep(1)
        except (HTTPError, URLError, TimeoutError) as error:
            print(
                f"Scheduler waiting for the API ({type(error).__name__}).", flush=True
            )
        time.sleep(60)
