# Memory Service

**Port:** 8002 (HTTP) | 50052 (gRPC)  
**Role:** Semantic memory store — persists and retrieves research context using vector embeddings.

## Responsibilities
- Store query/response pairs as vector embeddings in Qdrant
- Retrieve semantically similar past context for new queries (scoped per user)
- Provide fast context injection into the research pipeline without re-running web searches

## HTTP Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/memory/store` | Store a query/response pair |
| POST | `/memory/search` | Semantic search for relevant context |
| GET | `/memory/health` | Health check |

## gRPC Interface
- `StoreMemory(query_id, query, response, user_id)` — used by research-service formatter node
- `SearchMemory(query, limit, user_id)` → `contexts[]` — used by research-service context_retrieval node

## Vector Storage Details
- **Database:** Qdrant (embedded file mode or server mode via `QDRANT_URL`)
- **Collection:** `research_memory`
- **Embedding model:** `BAAI/bge-small-en-v1.5` via fastembed (384-dimensional vectors)
- **Distance metric:** Cosine similarity
- **Score threshold:** 0.6 (results below this are filtered out)
- **User scoping:** Qdrant payload filter on `user_id` field — each user only retrieves their own memories

## Stored Payload per Point
```json
{
  "query_id": "uuid",
  "query": "original query text",
  "response_snippet": "first 500 chars of response",
  "timestamp": "ISO datetime",
  "user_id": "user uuid"
}
```

## Architecture Pattern
Hexagonal (Ports & Adapters):
- `domain/service.py` — MemoryDomainService
- `domain/ports.py` — IMemoryRepository
- `domain/models.py` — MemoryRecord, ContextSearchRequest, ContextSearchResult
- `adapters/inbound/http_router.py` — FastAPI endpoints
- `adapters/inbound/grpc_server.py` — gRPC server
- `adapters/outbound/qdrant_adapter.py` — QdrantMemoryAdapter (implements IMemoryRepository)
- `application/use_cases.py` — StoreMemoryUseCase, SearchMemoryUseCase

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `QDRANT_URL` | _(empty — uses embedded mode)_ | Qdrant server URL (Docker mode) |
| `QDRANT_PATH` | `/data/qdrant_db` | Local path for embedded Qdrant |
| `QDRANT_COLLECTION` | `research_memory` | Collection name |
