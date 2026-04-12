"""
Outbound adapter: calls Ollama via LangChain for structured JSON output.
Implements the ILLMPort domain port.
"""
import json
import logging

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage

from ...domain.ports import ILLMPort

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = """You are an intent classification engine for a developer research assistant.

Classify the user query and return ONLY a JSON object with these exact keys:
{
  "confidence_score": <float 0.0-1.0>,
  "is_clear": <bool>,
  "clarification_question": "<string, empty if is_clear=true>",
  "category": "<one of: BUG, ARCHITECTURE, CONCEPT, COMPARISON, RESEARCH, GENERAL, NON_TECHNICAL>"
}

Categories:
- BUG: debugging, error messages, stack traces
- ARCHITECTURE: system design, patterns, scalability
- CONCEPT: explain how X works, what is X
- COMPARISON: X vs Y, trade-offs between X and Y
- RESEARCH: open-ended deep-dive topics
- GENERAL: simple factual technical questions
- NON_TECHNICAL: off-topic, non-technical

Rules:
- is_clear=true only if confidence_score >= 0.8
- Set clarification_question if the query is ambiguous
- Return ONLY the JSON, no extra text
"""


class OllamaLLMAdapter(ILLMPort):
    def __init__(self, base_url: str, model_name: str, timeout: int = 120) -> None:
        self._llm = ChatOllama(
            base_url=base_url,
            model=model_name,
            temperature=0.0,
            request_timeout=timeout,
        )

    async def classify_intent(self, query: str, history: list[dict]) -> dict:
        history_text = ""
        if history:
            lines = [f"{m['role'].upper()}: {m['content']}" for m in history[-4:]]
            history_text = "\nConversation history:\n" + "\n".join(lines) + "\n"

        messages = [
            SystemMessage(content=_SYSTEM_PROMPT),
            HumanMessage(content=f"{history_text}\nQuery: {query}"),
        ]

        try:
            response = await self._llm.ainvoke(messages)
            raw_text = response.content.strip()

            # Strip markdown code fences if present
            if raw_text.startswith("```"):
                raw_text = raw_text.split("```")[1]
                if raw_text.startswith("json"):
                    raw_text = raw_text[4:]

            return json.loads(raw_text)

        except (json.JSONDecodeError, Exception) as exc:
            logger.warning("LLM classification failed: %s", exc)
            return {
                "confidence_score": 0.5,
                "is_clear": False,
                "clarification_question": "Could you clarify your question?",
                "category": "GENERAL",
            }
