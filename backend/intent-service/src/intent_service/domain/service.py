"""
Domain service for intent classification.
Depends only on abstract ports — no framework, no HTTP, no ORM.
"""
from .models import ClassificationRequest, IntentClassification, QueryCategory
from .ports import IIntentClassifier, ILLMPort


class IntentDomainService(IIntentClassifier):
    """
    Core business logic:
    1. Call the LLM via ILLMPort to get raw classification.
    2. Parse and validate the result into a domain model.
    3. Apply business rules (e.g. NON_TECHNICAL always not clear).
    """

    def __init__(self, llm_port: ILLMPort) -> None:
        self._llm = llm_port

    async def classify(self, request: ClassificationRequest) -> IntentClassification:
        raw = await self._llm.classify_intent(request.query, request.history)

        category = QueryCategory(raw.get("category", "GENERAL"))
        confidence = float(raw.get("confidence_score", 0.0))
        is_clear = bool(raw.get("is_clear", False))
        clarification = str(raw.get("clarification_question", ""))

        # Business rule: non-technical queries are always rejected
        if category == QueryCategory.NON_TECHNICAL:
            is_clear = False
            clarification = (
                "I specialise in technical and software-engineering topics. "
                "Could you rephrase with a technical angle?"
            )

        return IntentClassification(
            confidence_score=confidence,
            is_clear=is_clear,
            category=category,
            clarification_question=clarification,
        )
