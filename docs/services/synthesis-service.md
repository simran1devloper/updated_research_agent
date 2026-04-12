# Synthesis Service

**Port:** 8004 (HTTP) | 50054 (gRPC)  
**Role:** LLM synthesis engine — generates structured research reports and performs gap analysis.

## Responsibilities
- Synthesise research data into structured technical reports using an LLM
- Stream report tokens live to the research-service (and on to the frontend)
- Perform gap analysis — score research confidence and identify missing topics
- Generate Mermaid diagrams inline when architecture/flow visualisation is appropriate

## HTTP Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/synthesis/synthesize` | Generate a full report (blocking) |
| POST | `/synthesis/synthesize/stream` | Stream report tokens (SSE) |
| POST | `/synthesis/gaps` | Analyse research gaps |
| GET | `/synthesis/health` | Health check |

## gRPC Interface
- `Synthesize(query, research_data[], history[], gaps[])` → `SynthesisResponse`
- `SynthesizeStream(...)` → streaming tokens
- `AnalyzeGaps(query, research_data[], iteration)` → `{ confidence_score, gaps[] }`

## Report Structure (LLM-prompted)
1. Executive Summary (2–3 sentences)
2. Structured sections with headings
3. Inline citations `[1]`, `[2]` matching source numbers
4. Optional Mermaid diagram (flowchart TD or sequenceDiagram, max 10 nodes)
5. Key Takeaways (3–5 bullet points)

## Gap Analysis Response
```json
{
  "confidence_score": 0.75,
  "gaps": ["specific missing topic 1", "specific missing topic 2"]
}
```
- `confidence_score >= 0.8` → research is sufficient, proceed to synthesis
- `gaps[]` → specific searchable topics for the next deep_research iteration

## LLM Backend
- **Adapter:** `OllamaLLMAdapter` using `langchain-ollama`
- **Model:** configurable via `OLLAMA_MODEL_NAME` (default: `ministral-3:latest`)
- **Temperature:** 0.1 (deterministic, factual output)
- **Streaming:** `astream()` for live token delivery

## Architecture Pattern
Hexagonal (Ports & Adapters):
- `domain/service.py` — SynthesisDomainService
- `domain/ports.py` — ILLMPort
- `domain/models.py` — SynthesisRequest, SynthesisResult
- `prompts/templates.py` — `build_synthesis_prompt()`, `build_gap_analysis_prompt()`
- `adapters/inbound/http_router.py` — FastAPI endpoints
- `adapters/inbound/grpc_server.py` — gRPC server
- `adapters/outbound/ollama_adapter.py` — OllamaLLMAdapter

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_BASE_URL` | `http://host.docker.internal:11434` | Ollama server URL |
| `OLLAMA_MODEL_NAME` | `ministral-3:latest` | LLM model |
| `OLLAMA_TIMEOUT` | `120` | Request timeout in seconds |
