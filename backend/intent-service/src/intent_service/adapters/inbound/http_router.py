"""
Inbound adapter: FastAPI router for the Intent Service.
Translates HTTP requests → application use-cases → HTTP responses.
"""
from fastapi import APIRouter, Depends
from shared.models import IntentRequest, IntentResponse, HealthResponse, QueryCategory

from ...application.use_cases import ClassifyIntentUseCase
from ...container import IntentContainer

router = APIRouter(prefix="/intent", tags=["intent"])


def _get_use_case() -> ClassifyIntentUseCase:
    return IntentContainer.instance().classify_intent_use_case()


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(service="intent-service")


@router.post("/classify", response_model=IntentResponse)
async def classify_intent(
    body: IntentRequest,
    use_case: ClassifyIntentUseCase = Depends(_get_use_case),
) -> IntentResponse:
    result = await use_case.execute(query=body.query, history=body.history)
    return IntentResponse(
        confidence_score=result.confidence_score,
        is_clear=result.is_clear,
        clarification_question=result.clarification_question,
        category=QueryCategory(result.category.value),
    )
