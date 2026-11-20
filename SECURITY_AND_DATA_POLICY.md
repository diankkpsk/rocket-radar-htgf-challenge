# Security and data policy

FounderRadar is a single-user research application served on loopback. It needs authenticated access control, transport protection, request protections and a deployment review before use as a shared internet service.

## Evidence and professional data

Collect only public professional information from named publisher adapters and official registers. Store short necessary excerpts, professional founder names with citations, dates and technical/company facts. A programme listing, award, registration and funding announcement each have distinct evidentiary value. Keep unknown fields null and preserve uncertainty. TEST FIXTURE — NOT REAL entries belong only in isolated tests.

The package stores attributable observations and a manifest of capture inputs. Original pages remain owned by their publishers. Review current source terms and licensing before operational or commercial reuse. A robots permission describes technical crawl permission. Source notes include HTGF's search-use signal and restrictions on AI use. Search is deterministic, with no LLM provider or training workflow.

## Network and content handling

Automated requests are limited to explicit public hosts and approved paths. Website and registry clients resolve public addresses, pin the connection to the validated IP and validate TLS against the hostname. Responses have timeouts, bounded reads and content checks. Website collection respects robots and crawl delay. Redirects fail visibly. Manual URL inbox entries are validated and stored for review, without fetching arbitrary addresses.

Scraped content supplies data and never executes instructions. Rendered text is escaped and links accept HTTP/HTTPS only. API mutations require JSON and reject cross-site browser requests. Host validation, CSP, frame denial and no-referrer protect the local workspace. CSV exports neutralize spreadsheet formula prefixes. Requests and errors redact configured adapter secrets. Secret values remain in the local environment or ignored .env file.

## Persistence and retention

SQLite transactions and foreign keys guard partial ingestion. A unique active-scan constraint prevents parallel scans against a single database. One server worker is supported. Back up var/radar.sqlite3 using SQLite's backup mechanism or while the server is stopped. Restrict workstation access to the local database and exports.

A suggested operational retention policy is to review evidence and founder names every 180 days and remove unnecessary or contested material promptly. This edition requires that operator review. It has no automatic retention deletion. Inspect the source URL again before acting on stale evidence.

Use the deletion utility for a publisher or subject removal request after verifying the requested scope. It first creates a recoverable SQLite backup and records a suppression key. A suppressed venture is skipped during future live/replay ingestion. Stop the app before changing packaged source recordings for redistribution. Manual inbox items and analyst exports should also be checked for the affected material.

## Restricted platforms and limits

Private groups, login walls, CAPTCHAs and paid-access restrictions are outside automated collection. Social network integrations remain manual unless a current legitimate API implementation is configured. The country directory supplies capability labels. Its presence makes no assertion of licensed bulk access.

This local MVP has no consent management platform, external sharing, email alerts, organizational audit identity or multi-user access control. Review decisions refer to the local analyst session. Operator responsibility includes lawful basis, information obligations, legitimate interests, retention, source permissions and responding to data requests.
