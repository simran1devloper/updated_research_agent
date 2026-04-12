# Conversation Service

**Port:** 8008 (HTTP) | 50056 (gRPC)  
**Role:** Persistent conversation store — manages threads and message history.

## Responsibilities
- Create and manage conversation threads (scoped per user)
- Append and retrieve messages (user + assistant turns)
- Provide conversation history to the research-service for context-aware responses
- Expose thread/message CRUD over both HTTP (frontend) and gRPC (research-service)

## HTTP Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/conversation/threads` | List all threads for the authenticated user |
| POST | `/conversation/threads` | Create a new thread |
| GET | `/conversation/threads/{id}` | Get thread by ID |
| DELETE | `/conversation/threads/{id}` | Delete thread and all its messages |
| GET | `/conversation/threads/{id}/messages` | Get messages for a thread (paginated) |
| POST | `/conversation/threads/{id}/messages` | Append a message to a thread |
| GET | `/conversation/health` | Health check |

## gRPC Interface
- `EnsureThread(thread_id, user_id, title)` — create thread if it doesn't exist
- `GetHistory(thread_id, limit)` → `messages[]` — used by research-service to load context
- `AppendMessage(thread_id, role, content)` — used by research-service formatter/stream nodes

## Domain Model
- `Thread` — id, user_id, title, created_at
- `Message` — id, thread_id, role (`user`|`assistant`), content, metadata (JSON), created_at

## Storage
- SQLite via SQLAlchemy async (`aiosqlite`)
- Database path: `/data/conversations.db` (Docker volume)

## Architecture Pattern
Hexagonal (Ports & Adapters):
- `domain/models.py` — Thread, Message
- `domain/ports.py` — IThreadRepository, IMessageRepository
- `application/use_cases.py` — thread and message use cases
- `adapters/inbound/http_router.py` — FastAPI endpoints
- `adapters/inbound/grpc_server.py` — gRPC server
- `adapters/outbound/repositories.py` — SQLAlchemy repositories
- `db/` — async session + table definitions

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CONVERSATION_DB_URL` | `sqlite+aiosqlite:////data/conversations.db` | Database connection string |
