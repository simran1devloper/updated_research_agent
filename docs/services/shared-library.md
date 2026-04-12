# Shared Library

**Package:** `shared` (installed as editable package in all services)  
**Role:** Common contracts, observability, and utilities shared across all microservices.

## Modules

### `models.py` — Shared Pydantic DTOs
API-level data transfer objects used as contracts between services. These are NOT domain models.

| DTO | Used By |
|-----|---------|
| `IntentRequest` / `IntentResponse` | intent-service |
| `MemoryStoreRequest` / `MemorySearchRequest` / `MemorySearchResponse` | memory-service |
| `SearchRequest` / `SearchResult` / `SearchResponse` | search-service |
| `SynthesisRequest` / `SynthesisResponse` | synthesis-service |
| `ResearchRequest` / `ResearchResponse` | research-service, api-gateway |
| `HealthResponse` | all services |

Enums: `QueryCategory`, `ResearchMode`, `ResearchStatus`

---

### `tracker.py` — ServiceTracker
Lightweight in-process observability tracker covering the full issue lifecycle:

| Stage | Method | Description |
|-------|--------|-------------|
| **Prevention** | `tracker.prevent(rule, condition, context)` | Assert preconditions before execution; raises `ValueError` on failure |
| **Detection** | `async with tracker.detect(operation, context)` | Measures latency, captures exceptions, logs slow calls (>5s) |
| **Avoidance** | `tracker.avoid(metric, current, threshold)` | Emits warning when metric approaches dangerous threshold |
| **Rectification** | `tracker.rectify(exc, operation, context)` | Records structured error with full traceback for post-mortem |

Additional helpers:
- `tracker.check_error_rate(operation, threshold=0.3)` — computes error rate and calls `avoid()`
- `tracker.recent_issues(stage, limit)` → list of issue records
- `tracker.stats()` → per-operation call/error counts and error rates

All records stored in a rolling in-memory deque (max 200 entries) and emitted through the service logger.

---

### `middleware.py` — ObservabilityMiddleware
Drop-in FastAPI middleware. Call `add_observability(app, service_name)` in any service `main.py`.

What it does automatically:
- Logs every request: method, path, status, latency
- Records slow requests (>5s) as `detection` issues
- Records 5xx responses as `rectification` issues
- Mounts `/health/issues` — recent tracked issues (filterable by stage)
- Mounts `/health/stats` — per-operation call/error counts

---

### `logger.py` — Structured Logger
- JSON-formatted rotating file logger
- Log files written to `logs/app.log` and `logs/error.log` per service
- Used by ServiceTracker and ObservabilityMiddleware

---

### `config.py` — Shared Configuration
Common environment variable loading utilities.

---

### `proto/` — gRPC Protobuf Definitions
Shared `.proto` files and generated stubs for inter-service gRPC communication.

## Usage in Services

```python
# In any service main.py
from shared.middleware import add_observability
add_observability(app, service_name="my-service")

# In any router or use case
from shared.middleware import get_tracker
tracker = get_tracker("my-service")
tracker.prevent("query-non-empty", condition=bool(query), context={"query": query})
async with tracker.detect("llm_call", context={"model": "ministral"}):
    result = await llm.invoke(prompt)
```
