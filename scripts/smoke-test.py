"""Read-only runtime check against an already running FounderRadar service."""

import argparse
import json
from urllib.request import urlopen

p = argparse.ArgumentParser(description=__doc__)
p.add_argument("--port", type=int, default=8766)
args = p.parse_args()
base = f"http://127.0.0.1:{args.port}"
for path in [
    "/health",
    "/api/v1/stats",
    "/api/v1/leads?kind=portfolio&q=robotics",
    "/api/v1/sources",
    "/api/v1/coverage",
    "/api/v1/evaluation",
    "/api/v1/discovery/plan?country=DE&technology=robotics",
]:
    with urlopen(base + path, timeout=10) as response:
        data = json.load(response)
        if path == "/health":
            assert data["status"] == "ok"
        if "kind=portfolio" in path:
            assert data["total"] > 0
        print(path, "OK", data.get("total", len(data.get("items", []))))
