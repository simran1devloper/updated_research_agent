"""Application use-case for search."""
from ..domain.models import SearchQuery, SearchResults
from ..domain.ports import ISearchOrchestrator


class ExecuteSearchUseCase:
    def __init__(self, orchestrator: ISearchOrchestrator) -> None:
        self._orchestrator = orchestrator

    async def execute(
        self,
        query: str,
        sites: list[str] | None = None,
        limit: int = 5,
        use_tavily: bool = True,
        use_google: bool = True,
    ) -> SearchResults:
        search_query = SearchQuery(
            query=query,
            sites=sites or [],
            limit=limit,
            use_tavily=use_tavily,
            use_google=use_google,
        )
        return await self._orchestrator.execute(search_query)
