"""
Outbound adapter: Qdrant vector database.
Implements IMemoryRepository using qdrant-client + fastembed.
"""
import logging
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import uuid

from ...domain.models import MemoryRecord, ContextSearchRequest, ContextSearchResult
from ...domain.ports import IMemoryRepository

logger = logging.getLogger(__name__)

_COLLECTION = "research_memory"
_VECTOR_SIZE = 384  # fastembed default (BAAI/bge-small-en-v1.5)


class QdrantMemoryAdapter(IMemoryRepository):
    def __init__(self, path: str, collection: str = _COLLECTION) -> None:
        self._collection = collection
        # Support both embedded (path) and server (QDRANT_URL) modes
        import os
        qdrant_url = os.getenv("QDRANT_URL", "")
        if qdrant_url:
            self._client = QdrantClient(url=qdrant_url)
        else:
            self._client = QdrantClient(path=path)
        self._ensure_collection()

    def _ensure_collection(self) -> None:
        existing = [c.name for c in self._client.get_collections().collections]
        if self._collection not in existing:
            self._client.create_collection(
                collection_name=self._collection,
                vectors_config=VectorParams(size=_VECTOR_SIZE, distance=Distance.COSINE),
            )
            logger.info("Created Qdrant collection: %s", self._collection)

    def _embed(self, text: str) -> list[float]:
        from fastembed import TextEmbedding
        model = TextEmbedding()
        embeddings = list(model.embed([text]))
        return embeddings[0].tolist()

    async def store(self, record: MemoryRecord) -> None:
        try:
            vector = self._embed(f"{record.query} {record.response[:200]}")
            self._client.upsert(
                collection_name=self._collection,
                points=[
                    PointStruct(
                        id=str(uuid.uuid4()),
                        vector=vector,
                        payload={
                            "query_id": record.query_id,
                            "query": record.query,
                            "response_snippet": record.response[:500],
                            "timestamp": record.timestamp,
                            "user_id": record.user_id,
                        },
                    )
                ],
            )
        except Exception as exc:
            logger.error("Failed to store memory: %s", exc)

    async def search(self, request: ContextSearchRequest) -> ContextSearchResult:
        try:
            vector = self._embed(request.query)
            # Build filter: if user_id provided, scope to that user only
            query_filter = None
            if request.user_id:
                from qdrant_client.models import Filter, FieldCondition, MatchValue
                query_filter = Filter(
                    must=[FieldCondition(key="user_id", match=MatchValue(value=request.user_id))]
                )
            hits = self._client.search(
                collection_name=self._collection,
                query_vector=vector,
                limit=request.limit,
                score_threshold=0.6,
                query_filter=query_filter,
            )
            contexts = [
                f"Q: {h.payload['query']}\nA: {h.payload['response_snippet']}"
                for h in hits
            ]
            return ContextSearchResult(contexts=contexts)
        except Exception as exc:
            logger.error("Failed to search memory: %s", exc)
            return ContextSearchResult(contexts=[])
