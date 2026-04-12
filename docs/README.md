# AI Research Agent — Project Documentation

> A production-grade, agentic AI research assistant built on a microservices architecture.  
> Designed to autonomously research technical topics, synthesise structured reports, and stream results live to users.

---

## The Problem

Knowledge workers and engineers spend hours manually searching, reading, and synthesising information from multiple sources to answer complex technical questions. Existing AI chat tools give single-shot answers with no transparency into how they arrived at conclusions, no memory of past research, and no ability to iteratively deepen their understanding when initial results are insufficient.

---

## The Solution

An autonomous AI research agent that:
- **Understands intent** — classifies what you're asking before acting
- **Searches the web** — pulls from multiple providers in parallel
- **Iterates until confident** — loops through gap analysis and re-search until confidence ≥ 80%
- **Synthesises structured reports** — executive summary, cited sections, Mermaid diagrams, key takeaways
- **Streams everything live** — users watch the pipeline execute node by node, token by token
- **Remembers past research** — semantic vector memory scoped per user
- **Persists conversations** — full thread history, resumable across sessions

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                        Next.js Frontend                          │
│         (Auth · Thread Management · Live SSE Streaming)          │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTPS / SSE
┌──────────────────────────▼──────────────────────────────────────┐
│                       API Gateway :8000                          │
│              (JWT Auth · Routing · Observability)                │
└──┬──────────────┬──────────────────────┬────────────────────────┘
   │              │                      │
   ▼              ▼                      ▼
Auth :8007  Conversation :8008    Research :8005
(JWT/OAuth)  (Thread/Msg CRUD)   (LangGraph Orchestrator)
                                         │
              ┌──────────────────────────┼──────────────────────────┐
              ▼                          ▼                           ▼
        Intent :8001             Memory :8002               Search :8003
     (LLM Classification)    (Qdrant Vector DB)        (Tavily/Google/DDG)
                                                               │
                                                               ▼
                                                      Synthesis :8004
                                                    (Ollama LLM Reports)
```

---

## Services at a Glance

| Service | Port (HTTP) | Port (gRPC) | Technology | Role |
|---------|-------------|-------------|------------|------|
| API Gateway | 8000 | — | FastAPI | Auth enforcement, routing |
| Auth Service | 8007 | 50055 | FastAPI + SQLite | Identity, JWT, OAuth |
| Research Service | 8005 | — | FastAPI + LangGraph | Agentic orchestrator |
| Intent Service | 8001 | 50051 | FastAPI + Ollama | Query classification |
| Memory Service | 8002 | 50052 | FastAPI + Qdrant | Semantic memory |
| Search Service | 8003 | 50053 | FastAPI + Tavily/Google/DDG | Web search |
| Synthesis Service | 8004 | 50054 | FastAPI + Ollama | LLM report generation |
| Conversation Service | 8008 | 50056 | FastAPI + SQLite | Thread/message persistence |
| Frontend | 3000 | — | Next.js 14 | User interface |

---

## The Research Pipeline (LangGraph)

Every query runs through a deterministic state machine with conditional routing:

```
guard
  └─► context_retrieval          (fetch past Q&A from vector memory)
        └─► intent_orchestrator  (LLM classifies query, checks clarity)
                ├─► clarify_user ──► END   (if query is unclear)
                └─► planner              (decides quick vs deep mode)
                        ├─► quick_mode ──► formatter ──► END
                        │   (memory context + LLM synthesis only)
                        └─► deep_research
                                └─► gap_analysis
                                        ├─► synthesize ──► formatter ──► END
                                        │   (confidence ≥ 0.8 or iter ≥ 3)
                                        └─► deep_research  (loop back)
```

**Quick mode** — triggered for GENERAL, BUG, CONCEPT queries. Uses cached memory context + LLM synthesis. Fast, no web search.

**Deep mode** — triggered for ARCHITECTURE, COMPARISON, RESEARCH queries. Iteratively searches the web, analyses gaps, and re-searches until confidence threshold is met (max 3 iterations).

---

## Data Flow: A Single Research Query

1. User types a query in the frontend and hits send
2. Frontend calls `POST /api/v1/research/run/stream` with Bearer token
3. API Gateway validates JWT via gRPC to auth-service, injects `X-User-ID`
4. Research service creates a `ResearchJob`, ensures thread exists in conversation-service
5. LangGraph pipeline starts:
   - `context_retrieval` → memory-service returns semantically similar past answers
   - `intent_orchestrator` → intent-service classifies query (e.g. `ARCHITECTURE`, `is_clear=true`)
   - `planner` → selects `deep` mode
   - `deep_research` → search-service runs Tavily + Google CSE in parallel, returns enriched results
   - `gap_analysis` → synthesis-service scores confidence (e.g. 0.65), returns gaps
   - `deep_research` (iteration 2) → re-searches with gap-specific sub-queries
   - `gap_analysis` → confidence now 0.87 ≥ 0.8 → proceed to synthesize
   - `synthesize` → synthesis-service streams report tokens via Ollama
   - `formatter` → stores result in memory-service, appends messages to conversation-service
6. Frontend receives SSE events in real time:
   - `node_start`/`node_end` → execution pipeline badges animate
   - `token` → report text streams character by character
   - `done` → sources, mode, iteration count, token usage displayed

---

## Authentication & Security

- **JWT Bearer tokens** — access (30 min) + refresh (7 days) with rotation
- **OAuth 2.0** — Google and GitHub login with auto-provisioning
- **Token validation** — gRPC call from gateway to auth-service (no shared secret in downstream services)
- **User scoping** — memory and conversation data filtered by `user_id` at the storage layer
- **Prevention checks** — input validation at every service boundary using the shared `ServiceTracker`

---

## Observability

Every service (backend and frontend) implements the same 4-stage observability pattern:

| Stage | What it catches | How |
|-------|----------------|-----|
| **Prevention** | Invalid inputs before execution | `tracker.prevent(rule, condition)` — raises on failure |
| **Detection** | Errors and slow operations as they happen | `async with tracker.detect(operation)` — wraps any async call |
| **Avoidance** | Metrics approaching dangerous thresholds | `tracker.avoid(metric, current, threshold)` — proactive warning |
| **Rectification** | Structured error records for post-mortem | `tracker.rectify(exc, operation, context)` — full traceback |

Each service exposes:
- `GET /health/issues` — recent issue records (filterable by stage)
- `GET /health/stats` — per-operation call counts, error counts, error rates

The frontend mirrors this pattern in `lib/observability.ts` with an in-memory ring buffer and structured JSON console logging.

---

## Communication Patterns

| Pattern | Used For |
|---------|---------|
| HTTP REST | Client → Gateway, Gateway → downstream services |
| Server-Sent Events (SSE) | Research streaming (gateway → frontend) |
| gRPC | High-frequency internal calls: auth validation, memory store/search, intent classification, synthesis |
| MCP (Model Context Protocol) | Research service exposes `/mcp/sse` for tool-based AI integrations |

---

## Technology Stack

### Backend
- **Python 3.11+** — all services
- **FastAPI** — HTTP framework
- **LangGraph** — agentic state machine for research orchestration
- **LangChain Ollama** — LLM integration (synthesis, intent classification)
- **Qdrant** — vector database for semantic memory
- **fastembed** — local embedding model (BAAI/bge-small-en-v1.5, 384-dim)
- **SQLAlchemy + aiosqlite** — async SQLite for auth and conversation persistence
- **gRPC / protobuf** — inter-service communication
- **Tavily, Google CSE, DuckDuckGo** — search providers
- **PyJWT + bcrypt** — auth primitives
- **Docker + Docker Compose** — containerisation

### Frontend
- **Next.js 14** (App Router) — React framework
- **TypeScript** — type safety
- **Tailwind CSS** — styling
- **shadcn/ui** — component library
- **Zustand** — state management
- **Framer Motion** — animations
- **Mermaid.js** — diagram rendering
- **Vitest** — unit testing
- **Playwright** — E2E testing

---

## Architecture Principles

**Hexagonal Architecture (Ports & Adapters)** — every service has:
- `domain/` — pure business logic, no framework dependencies
- `domain/ports.py` — abstract interfaces (what the domain needs)
- `adapters/inbound/` — HTTP and gRPC servers (how the world calls us)
- `adapters/outbound/` — database, LLM, and service clients (how we call the world)
- `application/use_cases.py` — orchestrates domain logic
- `container.py` — dependency injection wiring

This means every adapter is swappable without touching business logic. The LLM provider, database, or search engine can be replaced by implementing a new adapter.

---

## Deployment

### Local Development
```bash
# Start infrastructure (Qdrant)
docker compose -f docker-compose.infra.yml up -d

# Start all backend services
cd backend && bash main_runner.sh

# Start frontend
cd updated_frontend && pnpm dev
```

### Docker Compose (Full Stack)
```bash
# Set required env vars
cp .env.example .env
# Edit .env: TAVILY_API_KEY, JWT_SECRET, OLLAMA_BASE_URL, etc.

docker compose up --build
```

### Service Ports (local)
| Service | URL |
|---------|-----|
| Frontend | http://localhost:3000 |
| API Gateway | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| Auth Service | http://localhost:8007 |
| Research Service | http://localhost:8005 |
| Intent Service | http://localhost:8001 |
| Memory Service | http://localhost:8002 |
| Search Service | http://localhost:8003 |
| Synthesis Service | http://localhost:8004 |
| Conversation Service | http://localhost:8008 |
| Qdrant Dashboard | http://localhost:6333/dashboard |

---

## Key Design Decisions

**Why microservices?**  
Each capability (search, memory, synthesis, intent) has independent scaling needs, different external dependencies, and can be developed/deployed independently. The research orchestrator can be updated without touching the LLM or search layers.

**Why LangGraph over a simple chain?**  
LangGraph provides a stateful, inspectable, resumable graph with conditional routing. The quick/deep mode split, the gap analysis loop, and the clarification branch are all first-class graph edges — not if/else spaghetti.

**Why gRPC for internal calls?**  
High-frequency calls (token validation on every request, memory search on every query) benefit from gRPC's binary protocol and persistent connections. HTTP is used for less frequent or streaming calls.

**Why Qdrant + fastembed?**  
Qdrant runs embedded (no separate process in dev) or as a server (Docker). fastembed runs locally with no API key — zero external dependency for the memory layer.

**Why Ollama?**  
Fully local LLM inference — no API costs, no data leaving the machine. The model is swappable via environment variable.

---

## Pitch Summary

> **What:** An autonomous AI research agent that searches, iterates, and synthesises structured technical reports — streamed live to users.
>
> **How:** 8 specialised microservices orchestrated by a LangGraph state machine, with semantic memory, multi-provider web search, and a real-time Next.js frontend.
>
> **Why it's different:** Full pipeline transparency (users see every node execute), iterative confidence-based research (not single-shot), per-user semantic memory, and a fully local LLM stack with no vendor lock-in.
>
> **Built for:** Engineers, researchers, and knowledge workers who need deep, cited, structured answers — not chat responses.

---

## Repository Structure

```
AI_Agent_Microservices/
├── backend/
│   ├── api-gateway/          # Public entry point, JWT auth, routing
│   ├── auth-service/         # Identity, JWT, OAuth (Google/GitHub)
│   ├── research-service/     # LangGraph orchestrator, MCP server
│   ├── intent-service/       # LLM query classification
│   ├── memory-service/       # Qdrant vector memory
│   ├── search-service/       # Tavily + Google CSE + DuckDuckGo
│   ├── synthesis-service/    # Ollama LLM report generation
│   ├── conversation-service/ # Thread + message persistence
│   ├── shared/               # Shared DTOs, observability, logger
│   └── tests/                # Integration tests
├── updated_frontend/         # Next.js 14 frontend
│   ├── app/                  # Pages (App Router)
│   ├── components/           # UI components
│   ├── lib/                  # API client, store, observability
│   └── e2e/                  # Playwright E2E tests
├── docs/                     # This documentation
├── docker-compose.yml        # Full stack Docker Compose
└── docker-compose.infra.yml  # Infrastructure only (Qdrant)
```

---

## Documentation Index

- [API Gateway](./services/api-gateway.md)
- [Auth Service](./services/auth-service.md)
- [Research Service](./services/research-service.md)
- [Intent Service](./services/intent-service.md)
- [Memory Service](./services/memory-service.md)
- [Search Service](./services/search-service.md)
- [Synthesis Service](./services/synthesis-service.md)
- [Conversation Service](./services/conversation-service.md)
- [Shared Library](./services/shared-library.md)
- [Frontend](./frontend.md)
