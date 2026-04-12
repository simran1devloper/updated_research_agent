"""
Ports (interfaces) for the Intent Service domain.

Inbound ports  → what the application layer exposes to the outside world.
Outbound ports → what the domain needs from external systems (LLM, DB, …).

The domain NEVER imports concrete adapters — only these abstract interfaces.
"""
from abc import ABC, abstractmethod
from .models import ClassificationRequest, IntentClassification


# ---------------------------------------------------------------------------
# Inbound port  (driven by HTTP / tests / CLI)
# ---------------------------------------------------------------------------

class IIntentClassifier(ABC):
    """Primary port: classify the intent of a user query."""

    @abstractmethod
    async def classify(self, request: ClassificationRequest) -> IntentClassification:
        ...


# ---------------------------------------------------------------------------
# Outbound ports  (implemented by adapters)
# ---------------------------------------------------------------------------

class ILLMPort(ABC):
    """Secondary port: call an LLM for structured JSON classification."""

    @abstractmethod
    async def classify_intent(
        self,
        query: str,
        history: list[dict],
    ) -> dict:
        """
        Returns a raw dict with keys:
          confidence_score (float), is_clear (bool),
          clarification_question (str), category (str)
        """
        ...
