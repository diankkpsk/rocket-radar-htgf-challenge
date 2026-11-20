"""Install the locked runtime once, then serve the local research workspace."""

from __future__ import annotations
import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def environment():
    file = ROOT / ".env"
    if file.exists():
        for line in file.read_text().splitlines():
            if line.strip() and not line.lstrip().startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                if k.strip() in {
                    "FOUNDER_RADAR_PORT",
                    "FOUNDER_RADAR_DB",
                    "DATABASE_URL",
                    "COMPANIES_HOUSE_API_KEY",
                    "GITHUB_TOKEN",
                    "ENABLE_SCHEDULER",
                    "BRAVE_SEARCH_API_KEY",
                }:
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    if not os.environ.get("SSL_CERT_FILE") and Path("/etc/ssl/cert.pem").is_file():
        os.environ["SSL_CERT_FILE"] = "/etc/ssl/cert.pem"


def main():
    environment()
    try:
        import uvicorn
        import fastapi
        import alembic
    except ImportError:
        import venv

        folder = ROOT / ".venv"
        python = folder / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        if python.exists() and Path(sys.prefix).resolve() != folder.resolve():
            os.execv(str(python), [str(python), str(__file__), *sys.argv[1:]])
        if not python.exists():
            venv.create(folder, with_pip=True)
        subprocess.run(
            [
                str(python),
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                "-r",
                str(ROOT / "requirements.lock"),
            ],
            check=True,
        )
        os.execv(str(python), [str(python), str(__file__), *sys.argv[1:]])
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--port", type=int, default=int(os.getenv("FOUNDER_RADAR_PORT", "8766"))
    )
    parser.add_argument(
        "--init",
        action="store_true",
        help="Migrate and load the public evidence bundle, then exit.",
    )
    parser.add_argument(
        "--scheduler",
        action="store_true",
        help="Run the optional schedule client for an already running local server.",
    )
    args = parser.parse_args()
    if args.scheduler:
        from backend.scheduler import serve

        serve(args.port)
        return
    if args.init:
        from backend.api import initialize

        initialize()
        return
    import uvicorn

    uvicorn.run(
        "backend.api:app", host="127.0.0.1", port=args.port, workers=1, access_log=False
    )


if __name__ == "__main__":
    main()
