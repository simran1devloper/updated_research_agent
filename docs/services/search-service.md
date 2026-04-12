# Search Service

**Port:** 8003 (HTTP) | 50053 (gRPC)  
**Role:** Multi-provider web search — aggregates results from Tavily, Google CSE, and DuckDuckGo.

## Responsibilities
- Execute web searches across multiple providers in parallel
- Deduplicate results across providers
- Enrich thin snippets by fetching full page content
- Fall back to DuckDuckGo if primary providers return nothing

## HTTP Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/search/query` | Execute a search query |
| GET | `/search/health` | Health check |

## gRPC Interface
- `Search(query, limit, use_tavily, use_google, sites[])` → `SearchResults` — used by research-service

## Search Providers

| Provider | Role | Requires |
|----------|------|---------|
| Tavily | Primary — AI-optimised search | `TAVILY_API_KEY` |
| Google CSE | Site-specific or general search | `GOOGLE_API_KEY` + `GOOGLE_CSE_ID` |
| DuckDuckGo | Fallback — no API key needed | — |

## Search Orchestration Logic
1. If `use_tavily=true` → run Tavily search
2. If `sites[]` provided → run Google CSE per site (up to 3 sites)
3. If no sites but `use_google=true` → run Google CSE general search
4. If no tasks configured → use DuckDuckGo
5. All tasks run in parallel via `asyncio.gather`
6. Results are merged and deduplicated by URL
7. If combined results are empty → DuckDuckGo fallback
8. Snippets shorter than 200 chars → full page fetch via `WebFetcherAdapter`

## Result Schema
```json
{
  "results": [
    {
      "content": "page content or snippet",
      "source": "provider name",
      "url": "https://..."
    }
  ]
}
```

## Architecture Pattern
Hexagonal (Ports & Adapters):
- `domain/service.py` — SearchDomainService (orchestration logic)
- `domain/ports.py` — ISearchProvider, ISiteSearchProvider, IWebFetcher, ISearchOrchestrator
- `domain/models.py` — SearchQuery, SearchResults, SearchItem
- `adapters/inbound/http_router.py` — FastAPI endpoints
- `adapters/inbound/grpc_server.py` — gRPC server
- `adapters/outbound/tavily_adapter.py` — Tavily API adapter
- `adapters/outbound/google_cse_adapter.py` — Google Custom Search adapter
- `adapters/outbound/duckduckgo_adapter.py` — DuckDuckGo adapter
- `adapters/outbound/web_fetcher_adapter.py` — Full-page content fetcher

## Environment Variables

| Variable | Description |
|----------|-------------|
| `TAVILY_API_KEY` | Tavily search API key |
| `GOOGLE_API_KEY` | Google API key |
| `GOOGLE_CSE_ID` | Google Custom Search Engine ID |
