"""Domain models for the Search Service."""
from dataclasses import dataclass, field


@dataclass
class SearchQuery:
    query: str
    sites: list[str] = field(default_factory=list)
    limit: int = 5
    use_tavily: bool = True
    use_google: bool = True


@dataclass
class SearchItem:
    content: str
    source: str
    url: str


@dataclass
class SearchResults:
    items: list[SearchItem] = field(default_factory=list)

    def extend(self, other: "SearchResults") -> None:
        self.items.extend(other.items)

    def deduplicated(self) -> "SearchResults":
        seen: set[str] = set()
        unique: list[SearchItem] = []
        for item in self.items:
            if item.url not in seen:
                seen.add(item.url)
                unique.append(item)
        return SearchResults(items=unique)
