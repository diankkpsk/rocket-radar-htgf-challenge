"""Bounded HTTPS client for a fixed directory of public publisher hosts."""

from dataclasses import dataclass
import http.client
import ipaddress
import json
from pathlib import Path
import socket
import ssl
import time
import urllib.robotparser
from urllib.parse import urlsplit


class CollectionError(RuntimeError):
    pass


HOSTS = {"www.htgf.de", "www.tum.de", "www.kit-forge.de"}
AGENT = "FounderRadar/1.0 (public venture directory search)"
CONDITIONAL_CACHE = {}  # Holds a bounded number of permitted public HTML responses.


class PinnedConnection(http.client.HTTPSConnection):
    """Connect to exactly the address vetted by the allowlist/DNS checks."""

    def __init__(self, host, address, context):
        super().__init__(host, timeout=8, context=context)
        self.address = address

    def connect(self):
        sock = socket.create_connection((self.address, 443), timeout=self.timeout)
        try:
            self.sock = self._context.wrap_socket(sock, server_hostname=self.host)
        except BaseException:
            sock.close()
            raise


@dataclass
class Document:
    body: str
    status: int
    etag: str | None = None
    modified: str | None = None


class Fetcher:
    def __init__(self, max_requests=8, max_bytes=6_000_000):
        self.remaining = max_requests
        self.max_bytes = max_bytes
        self.robots = {}
        self.last_request = {}

    def _request(self, url, interval=1.0):
        uri = urlsplit(url)
        if (
            uri.scheme != "https"
            or uri.hostname not in HOSTS
            or uri.username
            or uri.password
            or uri.port not in (None, 443)
            or uri.fragment
        ):
            raise CollectionError(
                "Source URL is outside the permitted public directory"
            )
        if self.remaining <= 0:
            raise CollectionError("Per-scan request limit reached")
        self.remaining -= 1
        host = uri.hostname
        wait = interval - (time.monotonic() - self.last_request.get(host, 0))
        if wait > 0:
            time.sleep(wait)
        self.last_request[host] = time.monotonic()
        conn = None
        try:
            addresses = [
                item[4][0]
                for item in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
            ]
            if not addresses or any(
                not ipaddress.ip_address(ip).is_global for ip in addresses
            ):
                raise CollectionError(
                    "Source host did not resolve exclusively to public addresses"
                )
            cafile = "/etc/ssl/cert.pem"
            context = ssl.create_default_context(
                cafile=cafile if Path(cafile).is_file() else None
            )
            conn = PinnedConnection(host, addresses[0], context)
            headers = {
                "User-Agent": AGENT,
                "Accept": "text/html,application/json,text/plain",
                "Accept-Encoding": "identity",
            }
            previous = CONDITIONAL_CACHE.get(url)
            if previous and previous.etag:
                headers["If-None-Match"] = previous.etag
            if previous and previous.modified:
                headers["If-Modified-Since"] = previous.modified
            conn.request(
                "GET",
                uri.path + ("?" + uri.query if uri.query else ""),
                headers=headers,
            )
            res = conn.getresponse()
            if res.status == 304 and previous:
                return previous
            if res.status != 200:
                # No redirect following. Rate limits, denial and downtime remain visible.
                if res.status == 404 and uri.path == "/robots.txt":
                    return Document("", 404)
                error = CollectionError(
                    f"{host} returned HTTP {res.status} for {uri.path}"
                )
                if (
                    res.status == 400
                    and uri.path == "/wp-json/wp/v2/portfolio"
                    and res.headers.get_content_type() == "application/json"
                ):
                    try:
                        detail = json.loads(res.read(4096))
                        error.code = (
                            detail.get("code") if isinstance(detail, dict) else None
                        )
                    except (UnicodeDecodeError, ValueError):
                        pass
                raise error
            kind = res.headers.get_content_type()
            permitted = {"text/html", "text/plain", "application/xhtml+xml"}
            if host == "www.htgf.de" and uri.path == "/wp-json/wp/v2/portfolio":
                permitted.add("application/json")
            if kind not in permitted:
                raise CollectionError(f"Unsupported source content type: {kind}")
            if uri.path == "/robots.txt" and kind != "text/plain":
                raise CollectionError("Robots policy is not plain text")
            raw = res.read(self.max_bytes + 1)
            if len(raw) > self.max_bytes:
                raise CollectionError("Source exceeds response-size limit")
            doc = Document(
                raw.decode(
                    res.headers.get_content_charset() or "utf-8", errors="replace"
                ),
                200,
                res.headers.get("ETag"),
                res.headers.get("Last-Modified"),
            )
            if len(CONDITIONAL_CACHE) >= 18:
                CONDITIONAL_CACHE.pop(next(iter(CONDITIONAL_CACHE)))
            CONDITIONAL_CACHE[url] = doc
            return doc
        except (OSError, LookupError, http.client.HTTPException) as exc:
            raise CollectionError(f"{host}: {exc}") from exc
        finally:
            if conn:
                conn.close()

    def get(self, url):
        host = urlsplit(url).hostname
        if host not in HOSTS:
            raise CollectionError("Unlisted source host")
        if host not in self.robots:
            doc = self._request("https://" + host + "/robots.txt")
            rules = urllib.robotparser.RobotFileParser()
            rules.parse(doc.body.splitlines())
            self.robots[host] = rules
        rules = self.robots[host]
        if not rules.can_fetch(AGENT, url):
            raise CollectionError("Publisher robots policy denies this URL")
        delay = rules.crawl_delay(AGENT) or 1
        rate = rules.request_rate(AGENT)
        if rate and rate.requests > 0:
            delay = max(delay, rate.seconds / rate.requests)
        if delay > 12:
            raise CollectionError(
                "Publisher crawl interval exceeds this scan's time budget"
            )
        return self._request(url, float(delay)).body
