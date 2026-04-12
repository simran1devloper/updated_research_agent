# Intent Service

**Port:** 8001 (HTTP) | 50051 (gRPC)  
**Role:** Query classifier — determines what the user is asking and whether it needs clarification.

## Responsibilities
- Classify incoming queries into one of 7 categories using an LLM
- Determine if the query is clear enough to proceed or needs clarification
- Enforce the business rule that non-technical queries are always rejected
- Expose classification via both HTTP (health/testing) and gRPC (production path)

## HTTP Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/intent/classify` | Classify a query |
| GET | `/intent/health` | Health check |

## gRPC Interface
- `ClassifyIntent(query, history)` → `IntentClassification` — used by research-service

## Query Categories

| Category | Description |
|----------|-------------|
| `BUG` | Debugging, error diagnosis |
| `ARCHITECTURE` | System design, patterns |
| `CONCEPT` | Explanations, how-things-work |
| `COMPARISON` | Technology comparisons |
| `RESEARCH` | Open-ended research topics |
| `GENERAL` | General technical questions |
| `NON_TECHNICAL` | Rejected — always returns clarification request |

## Classification Response

```json
{
  "confidence_score": 0.92,
  "is_clear": true,
  "category": "ARCHITECTURE",
  "clarification_question": ""
}
```

## Business Rules
- `NON_TECHNICAL` queries always set `is_clear=false` with a fixed clarification message
- `confidence_score < threshold` (set by research-service) triggers clarification flow
- History is passed to the LLM for context-aware classification

## Architecture Pattern
Hexagonal (Ports & Adapters):
- `domain/service.py` — IntentDomainService (pure business logic)
- `domain/ports.py` — IIntentClassifier, ILLMPort
- `adapters/inbound/http_router.py` — FastAPI endpoints
- `adapters/inbound/grpc_server.py` — gRPC server
- `adapters/outbound/ollama_adapter.py` — Ollama LLM adapter
- `application/use_cases.py` — ClassifyIntentUseCase

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_BASE_URL` | `http://host.docker.internal:11434` | Ollama server URL |
| `OLLAMA_MODEL_NAME` | `ministral-3:latest` | LLM model for classification |
| `OLLAMA_TIMEOUT` | `120` | Request timeout in seconds |
