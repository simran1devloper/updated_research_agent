"""
Application layer use-cases for the Intent Service.
Thin orchestration — delegates all logic to the domain service.
"""
from ..domain.models import ClassificationRequest, IntentClassification
from ..domain.ports import IIntentClassifier


class ClassifyIntentUseCase:
    """Classify the intent of a user query."""

    def __init__(self, classifier: IIntentClassifier) -> None:
        self._classifier = classifier

    async def execute(
        self,
        query: str,
        history: list[dict] | None = None,
    ) -> IntentClassification:
        request = ClassificationRequest(query=query, history=history or [])
        return await self._classifier.classify(request)
