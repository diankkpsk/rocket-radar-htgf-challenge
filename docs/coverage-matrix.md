# Registry and developer-source coverage

The country catalogue contains 49 European and associated jurisdictions. Search it by country, ISO code, register name or access mode in Sources, through `GET /api/v1/coverage`, or with `python3 -m registries coverage Germany`. The underlying metadata is in `registries/directory.csv` and `registries/coverage.py`. The 45 entries marked `planned` are research starting points supplied in the brief. Their current API availability, licence, cost and publication cadence remain unverified. BRIS offers interactive company lookup. FounderRadar has no EU-wide registration feed.

## Implemented modes

| Country | Source and mode | Evidence from this build, 20 Nov 2026 | Interpretation |
|---|---|---|---|
| Norway | Brønnøysund Register Centre, public API | A real, one-page query returned eight records. The response was normalized and saved at 14:18:50 UTC. | The 30-day demonstration required AS company form, an eligible primary industry, recent foundation and recent first registration in the CCR. The captured page is a sample of the query. |
| United Kingdom | Companies House, keyed advanced search | Three actual public company pages were reviewed at 14:15 UTC. The authenticated adapter was tested with synthetic responses. The live API key was absent. | The record ID, legal name, incorporation date and filed SIC codes are sourced. A code provides an industry clue. Product, team, customers and funding need separate evidence. |
| Estonia | e-Business Register, operator-supplied official snapshot | CSV and ZIP imports, date validation, duplicate IDs and first-appearance comparison were tested with labeled synthetic input. No operator-downloaded production snapshot was supplied. | An eligible limited company must have a qualifying first-entry date in the selected window. Presence in a newly obtained file only dates the observation. |
| Germany | Joint register portal, manual notice review | Validation tests cover incorporations, later entries, court-specific numbers, session links and effective dates. No historical German notice is preloaded. | An analyst checks the primary document. Incorporation requires an explicit initial entry date. Amendments, relocations, branches and publication notices have their own event types. |

The three UK records can be compared directly with their source pages. Each has a distinct identifier and first-registration date. The application deliberately omits registered-office addresses and personal details. [KYE ROBOTICS LTD](https://find-and-update.company-information.service.gov.uk/company/SC908316), [ORBITAL DATA TECHNOLOGY LTD](https://find-and-update.company-information.service.gov.uk/company/17537888), [VISTARA SOFTWARE LTD](https://find-and-update.company-information.service.gov.uk/company/17431091).

### Norway

`python3 -m registries norway --days 30 --page-size 8` prints one live page. Add `--as-of YYYY-MM-DD` for a historical window and `--cursor 1` for page two. Both date filters are inclusive. The scan accepts primary industry branches `62.1`, `72.1` and `26.1`. The underlying source can include earlier foundations, personal businesses and sub-entities, which this adapter excludes. The stored records preserve `formed_at` alongside `registered_at`. The UI sample was collected using `days=30, page_size=8`. It is reproducible from `registries/norway_capture.json` without a network connection.

Contains data from Brønnøysundregistrene licensed under the Norwegian Licence for Open Government Data (NLOD) 2.0. FounderRadar normalizes and selects fields from the register. The source supplies the organisation number, which links to its full official JSON record. [API specification](https://data.brreg.no/enhetsregisteret/api/dokumentasjon/en/index.html), [licence](https://data.norge.no/nlod/en/2.0).

### United Kingdom

Use a Companies House developer account to create an application and a live REST API key. Set `COMPANIES_HOUSE_API_KEY` in the local process environment and restart the app. The key supplies the username for HTTP Basic authentication over TLS. `python3 -m registries uk --days 7 --page-size 20` queries active UK limited companies and public limited companies using technology SIC codes `72190`, `62012`, `71121` and `26110`. A caller may supply up to eight codes through the Python interface. The adapter validates response dates, company type and SIC codes again. [Getting started](https://developer.company-information.service.gov.uk/get-started), [authentication](https://developer.company-information.service.gov.uk/authentication), [advanced company search](https://developer-specs.company-information.service.gov.uk/companies-house-public-data-api/reference/search/advanced-company-search).

The documented service limit is 600 requests per five minutes. FounderRadar defaults to two pages of twenty, with an absolute maximum of three requests of forty rows per run. `next_cursor` is the next result offset. A rate limit or server failure is reported in the batch, and a partial run retains successful pages. A missing credential makes zero network requests. The three pictured UK registry entries came from manual review of the public overview pages. Their evidence capture method remains `recorded_public_page`. [Developer guidelines](https://developer.company-information.service.gov.uk/developer-guidelines), [response fields](https://developer-specs.company-information.service.gov.uk/companies-house-public-data-api/resources/a-list-of-companies?v=latest).

### Estonia

At the official download page, review the licence and obtain the **Basic data** CSV archive. An operator can inspect locally normalized results with the command below. The first-entry field is `ettevotja_esmakande_kpv`. The importer retains only current eligible limited companies and legal fields. Foreign branches, nonprofit entities and individual entrepreneurs fall outside its supported company-form selection. [Official open datasets and conditions of reuse](https://avaandmed.ariregister.rik.ee/en/downloading-open-data).

```sh
python3 -m registries estonia /path/to/ettevotja_rekvisiidid__lihtandmed.csv.zip --days 30 --max-records 100
```

The parser streams the single CSV in place and keeps the row and result counts bounded. Limits are 50 MiB for a ZIP, 256 MiB uncompressed, 500,000 scanned rows and 500 returned records. It accepts UTF-8 or UTF-8 with BOM and semicolon or comma separators. Missing first dates are rejected. When a row or result cap is reached, the output reports partial coverage. `--as-of` selects the registration window's end. Pass `--previous /path/to/previous-scan.json` to compare against a prior successful scan with the same window. The `snapshot_first_appearance` flag can be true for later-observed companies with older first-entry dates. The importer operates on files selected by a local operator. API credentials or contracted services are unnecessary for this workflow. Each daily release represents the registry population and statuses described by RIK on its download page.

### Germany

Look up the record in the joint portal and review its original document. The manual validator accepts the legal name, register court, HRA/HRB number, official portal URL, event type, short supporting excerpt and explicit operator confirmation. Enter a publication date only if the notice supplies one. Where a stable document permalink is unavailable, preserve the portal URL and court/number combination. Links containing session credentials are rejected. Official portal access conditions and capacity limits apply. This implementation performs no automated portal requests. [Register portal](https://www.handelsregister.de/rp_web/), [portal information and terms](https://www.handelsregister.de/rp_web/information/welcome.xhtml).

### GitHub

`python3 -m registries github 'org:open62541 open62541 in:name'` searches public, active, original repositories. A live unauthenticated request using this exact query and a page size of one returned `open62541/open62541` on 20 Nov 2026. This exercised the API. It produced no startup claim. The response retains organization attribution when available, dates, licence ID, topics, homepage and stars. Human owners are omitted. Attach technical evidence to a team only after independent source linkage. Release contents, README bodies and contributor histories are outside this adapter's scope. An optional `GITHUB_TOKEN` adds authenticated public search capacity. [Repository search](https://docs.github.com/en/rest/search/search#search-repositories), [rate limits](https://docs.github.com/en/rest/using-the-rest-api/rate-limits-for-the-rest-api), [observed repository](https://github.com/open62541/open62541).

FounderRadar caps each GitHub request at twenty records, with page selection restricted to the first three pages. One process spaces search requests by at least 6.1 seconds. The adapter uses only fixed HTTPS API hosts, validates addresses at connection time, disables redirects, bounds response bytes and suppresses raw upstream error bodies. Authenticated keys never appear in results. Each request returns source failure and retry information when available. Re-running a scan after its cooldown is the recovery path.

## Validation

```sh
python3 -m unittest discover -s tests -p test_registries.py -v
```

The registry suite covers UK request shape, credential handling, date arithmetic, pagination, duplicate rows, rate limits, schema changes, Norwegian formation and registration semantics, local CSV/ZIP bounds, Estonian first-entry parsing, DE notice categories and registry numbering, public-only GitHub signals, directory coverage and rejection of private network destinations. Synthetic input is confined to the test module. The evidence loaded into the demonstration application is recorded real-world material.
