# Outbound discovery

Choose a country and an optional project or technology, such as photonic chips. The preview combines that text with the [configured intent phrases](../config/intent.json) in English, German, French, Italian, Spanish, Dutch and Polish. It shows 14 queries by default and accepts up to 42. The first seven cover all seven languages. Each query targets a country by name or searches within a domain. For example, a German preview can combine “Mitgründer gesucht” with the technology and Deutschland. Generating a preview works offline.

## Run one query

Set `BRAVE_SEARCH_API_KEY` in the environment of the FounderRadar server using a subscription with Web Search access. Selecting a query sends a single HTTPS request to Brave and displays up to five links with short descriptions. A country outside the connector’s supported Brave regions uses worldwide results and a country keyword. The public-web index and language filters can miss relevant projects. [Brave Web Search reference](https://api-dashboard.search.brave.com/api-reference/web/search/get) · [Search operators](https://api-dashboard.search.brave.com/documentation/resources/search-operators) · [Authentication](https://api-dashboard.search.brave.com/documentation/guides/authentication)

Open a publisher’s page to review the source. Use manual URL intake to submit the publisher URL and your own observation. FounderRadar keeps the provider’s titles, URLs and snippets only in the search response. Searches run on demand, with a one-second local request interval and a cooldown when the provider requests one. Without a key, the preview and manual intake remain available. [Brave Search API terms](https://api-dashboard.search.brave.com/documentation/resources/terms-of-service)

## Verification

On 20 November 2026, seven offline tests passed for query generation, validation, fixed destination, missing credentials, result handling, country fallback and rate limits. The test environment had no Brave subscription key. An authenticated live result remains unverified.
