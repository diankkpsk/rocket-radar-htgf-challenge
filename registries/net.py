"""Bounded JSON requests to three fixed first-party APIs. No caller-supplied hosts."""

from __future__ import annotations

import http.client
import ipaddress
import json
import socket
import ssl
import threading
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlencode

ENDPOINTS = {
    "companies_house": (
        "api.company-information.service.gov.uk",
        "/advanced-search/companies",
    ),
    "norway": ("data.brreg.no", "/enhetsregisteret/api/enheter"),
    "github": ("api.github.com", "/search/repositories"),
}
MAX_BYTES = 1_000_000
_locks = {k: threading.Lock() for k in ENDPOINTS}
_next_request = {k: 0.0 for k in ENDPOINTS}


class SourceError(Exception):
    def __init__(self, message, status=None, retry_after=None):
        super().__init__(message)
        self.status = status
        self.retry_after = retry_after


def utcnow():
    return (
        datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    )


def _retry_seconds(headers):
    raw = headers.get("Retry-After", "")
    if raw.isdigit():
        return int(raw)
    if raw:
        try:
            return max(0, int(parsedate_to_datetime(raw).timestamp() - time.time()))
        except (ValueError, TypeError, OverflowError):
            pass
    reset = headers.get("X-RateLimit-Reset", "")
    if reset.isdigit() and headers.get("X-RateLimit-Remaining") == "0":
        return max(0, int(reset) - int(time.time()) + 1)
    return None


def _request(host, path, headers):
    # Connect to the address we just checked, retaining the original host for TLS.
    addresses = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    if not addresses or any(
        not ipaddress.ip_address(a[4][0]).is_global for a in addresses
    ):
        raise SourceError("The source did not resolve to a public address.")
    ctx = ssl.create_default_context()
    deadline = time.monotonic() + 12
    for family, typ, proto, _, address in addresses[:3]:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            break
        raw = socket.socket(family, typ, proto)
        raw.settimeout(min(5, remaining))
        try:
            raw.connect(address)
            tls = ctx.wrap_socket(raw, server_hostname=host)
        except OSError:
            raw.close()
            continue
        conn = http.client.HTTPSConnection(host, timeout=8, context=ctx)
        conn.sock = tls
        try:
            tls.settimeout(8)
            conn.request("GET", path, headers=headers)
            response = conn.getresponse()
            if response.status != 200:
                raise SourceError(
                    f"Source returned HTTP {response.status}.",
                    response.status,
                    _retry_seconds(response.headers),
                )
            if "json" not in response.getheader("Content-Type", "").lower():
                raise SourceError("The source response was not JSON.")
            if response.getheader("Content-Encoding", "identity").lower() != "identity":
                raise SourceError("Unexpected compressed response.")
            body = response.read(MAX_BYTES + 1)
            if len(body) > MAX_BYTES:
                raise SourceError("Response exceeded the 1 MB limit.")
            try:
                data = json.loads(body)
            except (UnicodeDecodeError, ValueError, RecursionError):
                raise SourceError("Invalid JSON response.") from None
            if not isinstance(data, dict):
                raise SourceError("Unexpected API response schema.")
            return data
        finally:
            conn.close()
    raise SourceError("Could not establish a secure connection to the source.")


def fetch(endpoint, params, headers=None):
    host, path = ENDPOINTS[endpoint]
    query = urlencode(params, doseq=True)
    request_headers = {
        "User-Agent": "FounderRadar/1.0 (bounded public research)",
        "Accept": "application/json",
        "Accept-Encoding": "identity",
    }
    request_headers.update(headers or {})
    gap = 6.1 if endpoint == "github" else 1.0
    with _locks[endpoint]:
        delay = _next_request[endpoint] - time.monotonic()
        if delay > gap + 0.1:
            raise SourceError(
                "Source is in its requested cooldown period.", 429, int(delay) + 1
            )
        if delay > 0:
            time.sleep(delay)
        try:
            return _request(host, path + "?" + query, request_headers)
        except SourceError as err:
            if err.status == 429 or err.retry_after is not None:
                _next_request[endpoint] = time.monotonic() + (
                    err.retry_after if err.retry_after is not None else 60
                )
            raise
        except (OSError, http.client.HTTPException):
            raise SourceError(
                "Network or TLS failure reaching the official source."
            ) from None
        finally:
            _next_request[endpoint] = max(
                _next_request[endpoint], time.monotonic() + gap
            )
