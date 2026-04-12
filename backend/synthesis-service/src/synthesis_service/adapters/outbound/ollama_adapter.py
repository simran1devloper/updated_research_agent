"""Outbound adapter: Ollama LLM for synthesis and gap analysis."""
import json
import logging
from collections.abc import AsyncIterator

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage

from ...domain.ports import ILLMPort

logger = logging.getLogger(__name__)


class OllamaLLMAdapter(ILLMPort):
    def __init__(self, base_url: str, model_name: str, timeout: int = 120) -> None:
        self._llm = ChatOllama(
            base_url=base_url,
            model=model_name,
            temperature=0.1,
            request_timeout=timeout,
        )

    async def synthesize(self, prompt: str) -> tuple[str, int]:
        try:
            response = await self._llm.ainvoke([HumanMessage(content=prompt)])
            token_usage = getattr(response, "usage_metadata", {}) or {}
            tokens = token_usage.get("total_tokens", 0) if isinstance(token_usage, dict) else 0
            return response.content, tokens
        except Exception as exc:
            logger.error("Synthesis LLM call failed: %s", exc)
            return "Error: Could not generate synthesis report.", 0

    async def synthesize_stream(self, prompt: str) -> AsyncIterator[str]:
        try:
            async for chunk in self._llm.astream([HumanMessage(content=prompt)]):
                if chunk.content:
                    yield chunk.content
        except Exception as exc:
            logger.error("Synthesis stream failed: %s", exc)
            yield "Error: Could not stream synthesis report."

    async def analyze_gaps(self, prompt: str) -> dict:
        try:
            response = await self._llm.ainvoke([HumanMessage(content=prompt)])
            raw = response.content.strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            return json.loads(raw)
        except Exception as exc:
            logger.warning("Gap analysis LLM call failed: %s", exc)
            return {"confidence_score": 0.5, "gaps": []}
