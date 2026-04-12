"""Inbound HTTP adapter for the Search Service."""
from fastapi import APIRouter, Depends
from shared.models import SearchRequest, SearchResponse, SearchResult, HealthResponse

from ...application.use_cases import ExecuteSearchUseCase
from ...container import SearchContainer

router = APIRouter(prefix="/search", tags=["search"])


def _get_use_case() -> ExecuteSearchUseCase:
    return SearchContainer.instance().execute_search_use_case()


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(service="search-service")


@router.post("/", response_model=SearchResponse)
async def search(
    body: SearchRequest,
    use_case: ExecuteSearchUseCase = Depends(_get_use_case),
) -> SearchResponse:
    results = await use_case.execute(
        query=body.query,
        sites=body.sites,
        limit=body.limit,
        use_tavily=body.use_tavily,
        use_google=body.use_google,
    )
    return SearchResponse(
        results=[
            SearchResult(content=item.content, source=item.source, url=item.url)
            for item in results.items
        ]
    )
