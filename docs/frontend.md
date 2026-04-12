# Frontend — Next.js Application

**Framework:** Next.js 14 (App Router)  
**Port:** 3000 (dev) / configurable (Docker)  
**Stack:** TypeScript, Tailwind CSS, Zustand, shadcn/ui, Framer Motion

## Overview
A modern, real-time AI research assistant interface. Users authenticate, manage conversation threads, submit research queries, and watch the AI pipeline execute live via Server-Sent Events.

## Pages

| Route | Component | Description |
|-------|-----------|-------------|
| `/` | `AssistantLayout` (auth-guarded) | Main chat interface |
| `/login` | `LoginPage` | Email/password + OAuth login |
| `/register` | `RegisterPage` | Account creation |
| `/auth/callback` | OAuth callback | Reads tokens from URL params, stores them |

## Key Components

### `AssistantLayout`
Top-level shell: 256px sidebar + full-height chat panel.

### `Sidebar`
- Lists all conversation threads (loaded from conversation-service on mount)
- New thread creation
- Thread deletion
- Health status indicator

### `ChatPanel`
- Loads message history from conversation-service when switching threads (cached per session)
- Renders messages with animated entry
- Shows typing indicator during streaming
- Displays thread title and token stats in header

### `MessageInput`
- Submits queries via `streamResearch()` SSE
- Handles abort (cancel in-flight request)
- Builds execution pipeline steps from `node_start`/`node_end` events

### `ChatMessage`
- Renders user and assistant messages
- Assistant messages include `ExecutionPipeline` and `ContentRenderer`

### `ExecutionPipeline`
- Animated pill badges for each graph node
- Status: `pending` → `in-progress` → `completed` / `failed`
- Shows duration per node

### `ContentRenderer`
- Renders markdown with syntax highlighting
- Detects and renders Mermaid diagrams inline via `MermaidViewer`

### `TokenStats`
- Displays per-thread and total token usage from `useTelemetryStore`

## State Management (Zustand)

| Store | State |
|-------|-------|
| `useAuthStore` | Authenticated user, persisted to localStorage |
| `useChatStore` | Messages per thread (in-memory, source of truth is server) |
| `useThreadStore` | Thread list, current thread ID |
| `useTelemetryStore` | Token usage per thread and total |
| `useSettingsStore` | Budget limit setting |
| `useHealthStore` | Backend health status |

## API Client (`lib/api-client.ts`)

All API calls go through `apiFetch()` which:
1. Attaches `Authorization: Bearer <token>` header
2. On 401 → attempts token refresh (serialised, no duplicate refresh calls)
3. On refresh failure → clears tokens and redirects to `/login`
4. On 5xx → triggers avoidance alert

Key functions:
- `register(email, username, password)` → `AuthUser`
- `login(email, password)` → `TokenResponse`
- `logout(refreshToken)` → void
- `fetchThreads()` → `ServerThread[]`
- `fetchMessages(threadId, limit)` → `ServerMessage[]`
- `deleteServerThread(threadId)` → void
- `streamResearch(req, onEvent, signal)` → void (SSE)
- `checkHealth()` → `HealthResponse`

## Observability (`lib/observability.ts`)
Frontend mirror of the backend `ServiceTracker` pattern:

| Function | Stage | Description |
|----------|-------|-------------|
| `prevent(rule, condition, context)` | Prevention | Throws if condition false |
| `detect(operation, fn, context)` | Detection | Wraps async fn, tracks latency + errors |
| `avoid(metric, current, threshold)` | Avoidance | Warns when metric exceeds threshold |
| `rectify(err, operation, context)` | Rectification | Records structured error |
| `checkErrorRate(operation, threshold)` | Avoidance | Computes and checks error rate |
| `recentIssues(stage, limit)` | Inspection | Returns recent issue records |
| `stats()` | Inspection | Per-operation call/error counts |

All records stored in an in-memory ring buffer (max 200). Logs emitted as structured JSON to the browser console.

## SSE Streaming Flow
```
User submits query
    → MessageInput calls streamResearch()
    → POST /api/v1/research/run/stream (with Bearer token)
    → SSE events arrive:
        node_start  → add ExecutionStep (in-progress)
        node_end    → update ExecutionStep (completed)
        report_start → prepare streaming content
        token       → append chunk to assistant message content
        done        → finalise message with sources/mode/iterations
        clarification → show clarification question as assistant message
        error       → show error message
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_API_GATEWAY_URL` | `http://localhost:8000` | API Gateway URL |
| `NEXT_PUBLIC_AUTH_SERVICE_URL` | `http://localhost:8007` | Auth Service URL (direct, for auth calls) |
| `NEXT_PUBLIC_LOG_LEVEL` | `info` | Frontend log level (debug/info/warn/error) |

## Testing
- Unit tests: Vitest (`__tests__/`)
- E2E tests: Playwright (`e2e/`)
  - `auth.spec.ts` — login/register/logout flows
  - `chat.spec.ts` — message sending and streaming
  - `sidebar.spec.ts` — thread management
  - `accessibility.spec.ts` — a11y checks
  - `observability.spec.ts` — observability layer
