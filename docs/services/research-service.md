# Research Service

**Port:** 8005 (HTTP + MCP SSE at `/mcp/sse`)  
**Role:** Orchestrator — runs the full AI research workflow using a LangGraph state machine.

## Responsibilities
- Accept research queries and execute a multi-step agentic pipeline
- Route between quick (memory-only) and deep (web search + iterative gap analysis) modes
- Stream live execution events and token chunks to the frontend via SSE
- Persist results to memory-service and conversation-service
- Expose an MCP (Model Context Protocol) server for tool-based integrations

## HTTP Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/research/run` | Blocking research — returns full `ResearchResponse` |
| POST | `/research/run/stream` | Streaming research — SSE event stream |
| GET | `/research/health` | Health check |
| GET | `/mcp/sse` | MCP server SSE endpoint |

## LangGraph Workflow

```
guard → context_retrieval → intent_orchestrator
                                    │
                    ┌───────────────┴───────────────┐
                clarify_user (END)              planner
                                                    │
                                    ┌───────────────┴───────────────┐
                                quick_mode                    deep_research
                                    │                               │
                                formatter                     gap_analysis
                                    │                               │
                                   END              ┌──────────────┴──────────────┐
                                              (confidence≥0.8              deep_research
                                               or iter≥3)                  (loop back)
                                                    │
                                               synthesize → formatter → END
```

### Node Descriptions

| Node | What it does |
|------|-------------|
| `guard` | Initialises state, assigns query_id |
| `context_retrieval` | Fetches relevant past Q&A from memory-service (vector search) |
| `intent_orchestrator` | Calls intent-service to classify query and check clarity |
| `clarify_user` | Returns clarification question if intent is unclear |
| `planner` | Decides mode: `quick` for GENERAL/BUG/CONCEPT, `deep` for ARCHITECTURE/COMPARISON/RESEARCH |
| `quick_mode` | Synthesises answer from memory context only (no web search) |
| `deep_research` | Calls search-service with query + gap sub-queries |
| `gap_analysis` | Asks synthesis-service to score confidence and identify missing topics |
| `synthesize` | Calls synthesis-service to produce final structured report |
| `formatter` | Stores result in memory-service and appends messages to conversation-service |

## SSE Event Types (streaming)

| Event | Payload |
|-------|---------|
| `node_start` | `{ type, node }` |
| `node_end` | `{ type, node }` |
| `report_start` | `{ type }` |
| `token` | `{ type, chunk }` — live LLM token |
| `clarification` | `{ type, question }` |
| `done` | `{ type, sources, mode, iterations, token_usage }` |
| `error` | `{ type, message }` |

## Key Dependencies
- `intent-service` — HTTP/gRPC (query classification)
- `memory-service` — HTTP/gRPC (context retrieval + storage)
- `search-service` — HTTP/gRPC (web search)
- `synthesis-service` — HTTP/gRPC (LLM synthesis + gap analysis + streaming)
- `conversation-service` — HTTP/gRPC (history persistence)

## Architecture Pattern
Hexagonal (Ports & Adapters):
- `graph/` — LangGraph state machine (builder, nodes, state)
- `domain/models.py` — ResearchJob, ResearchResult, ResearchMode, ResearchStatus
- `domain/ports.py` — abstract interfaces for all downstream services
- `application/use_cases.py` — RunResearchUseCase, StreamResearchUseCase
- `adapters/inbound/http_router.py` — FastAPI endpoints
- `adapters/inbound/mcp_server.py` — MCP SSE server
- `adapters/outbound/` — HTTP clients for each downstream service
- `container.py` — dependency injection

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SERVICE_INTENT_URL` | `http://intent-service:8001` | Intent service URL |
| `SERVICE_MEMORY_URL` | `http://memory-service:8002` | Memory service URL |
| `SERVICE_SEARCH_URL` | `http://search-service:8003` | Search service URL |
| `SERVICE_SYNTHESIS_URL` | `http://synthesis-service:8004` | Synthesis service URL |
| `SERVICE_CONVERSATION_URL` | `http://conversation-service:8008` | Conversation service URL |
| `RESEARCH_MAX_ITERATIONS` | `3` | Max deep research loop iterations |
| `RESEARCH_CONFIDENCE_THRESHOLD` | `0.8` | Confidence score to stop iterating |
| `RESEARCH_MAX_TOKENS_PER_QUERY` | `5000` | Token budget per query |
