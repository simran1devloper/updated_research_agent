# API Gateway

**Port:** 8000  
**Role:** Single public entry point for all client traffic.

## Responsibilities
- JWT authentication enforcement via `JWTAuthMiddleware` (validates Bearer tokens on every request)
- Request routing to downstream microservices
- CORS handling
- Observability middleware — latency tracking, 5xx detection, `/health/issues`, `/health/stats`

## Routes Exposed to Clients

| Method | Path | Proxies To |
|--------|------|------------|
| POST | `/api/v1/research/run` | research-service |
| POST | `/api/v1/research/run/stream` | research-service (SSE) |
| GET/POST/DELETE | `/api/v1/conversations/*` | conversation-service |
| GET/POST/DELETE | `/api/v1/memory/*` | memory-service |
| GET | `/api/v1/health/` | aggregated health check |

## Auth Flow
1. Client sends `Authorization: Bearer <access_token>`
2. `JWTAuthMiddleware` validates the token via gRPC call to auth-service (`GRPC_AUTH_HOST:50055`)
3. On success, injects `X-User-ID` header into the forwarded request
4. Downstream services read `X-User-ID` — they never re-validate the token themselves

## Key Dependencies
- `auth-service` — gRPC port 50055 (token validation)
- `research-service` — HTTP port 8005
- `conversation-service` — HTTP port 8008
- `memory-service` — HTTP port 8002

## Environment Variables

| Variable | Description |
|----------|-------------|
| `SERVICE_RESEARCH_URL` | URL of research-service |
| `SERVICE_CONVERSATION_URL` | URL of conversation-service |
| `SERVICE_MEMORY_URL` | URL of memory-service |
| `GRPC_AUTH_HOST` / `GRPC_AUTH_GRPC_PORT` | Auth gRPC endpoint |

## Architecture Pattern
Hexagonal (Ports & Adapters):
- `routers/` — inbound HTTP adapters (research, memory, conversations, health)
- `adapters/auth_client.py` — outbound gRPC adapter to auth-service
- `adapters/service_clients.py` — outbound HTTP adapters to downstream services
- `container.py` — dependency injection wiring
- `middleware/auth.py` — JWT validation middleware
