"""Retriever protocol + implementations."""

import re
from datetime import UTC, datetime, timedelta
from typing import Protocol

import chromadb
import chromadb.api
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from pydantic import BaseModel

from hackday_45_talk_to_your_data.vector_store import (
    ASSET_CATALOG,
    DEFAULT_CHROMA_PATH,
    QUERY_HISTORY,
    QUOTA_METRICS,
)


class SourceChunk(BaseModel):
    collection: str
    content: str
    score: float


INTENT_COLLECTIONS: dict[str, list[str]] = {
    "asset": [ASSET_CATALOG],
    "cost": [QUERY_HISTORY, QUOTA_METRICS],
    "optimise": [ASSET_CATALOG, QUERY_HISTORY, QUOTA_METRICS],
}


class Retriever(Protocol):
    def retrieve(
        self,
        query: str,
        intent: str,
        project: str | None,
        dataset: str | None,
        time_range: str | None,
        user_email: str | None,
    ) -> list[SourceChunk]: ...


class MockRetriever:
    def retrieve(
        self,
        query: str,
        intent: str,
        project: str | None,
        dataset: str | None,
        time_range: str | None,
        user_email: str | None = None,
    ) -> list[SourceChunk]:
        collections = INTENT_COLLECTIONS.get(intent, [ASSET_CATALOG])
        return [
            SourceChunk(
                collection=col,
                content=(
                    f"[{col}] mock chunk for query={query!r} "
                    f"project={project!r} dataset={dataset!r} time_range={time_range!r}"
                ),
                score=1.0,
            )
            for col in collections
        ]


def _parse_cutoff(time_range: str | None) -> float | None:
    if not time_range or time_range == "all_time":
        return None
    m = re.match(r"last_(\d+)_days?", time_range)
    if not m:
        return None
    days = int(m.group(1))
    return (datetime.now(UTC) - timedelta(days=days)).timestamp()


def _build_where(conditions: list[dict[str, object]]) -> dict[str, object] | None:
    if not conditions:
        return None
    if len(conditions) == 1:
        return conditions[0]
    return {"$and": conditions}


class ChromaRetriever:
    def __init__(self, n_results: int = 20) -> None:
        self._n_results = n_results
        self._client = chromadb.PersistentClient(path=str(DEFAULT_CHROMA_PATH))
        self._ef = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")

    @classmethod
    def from_client(
        cls,
        client: chromadb.api.ClientAPI,
        ef: SentenceTransformerEmbeddingFunction | None = None,
        n_results: int = 20,
    ) -> "ChromaRetriever":
        """Create a retriever backed by the given client — useful for testing."""
        r = cls.__new__(cls)
        r._n_results = n_results
        r._client = client
        r._ef = ef or SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")
        return r

    def _get_collection(self, name: str):  # type: ignore[return]
        return self._client.get_or_create_collection(name=name, embedding_function=self._ef)  # type: ignore[arg-type]

    def retrieve(
        self,
        query: str,
        intent: str,
        project: str | None,
        dataset: str | None,
        time_range: str | None,
        user_email: str | None = None,
    ) -> list[SourceChunk]:
        collections = INTENT_COLLECTIONS.get(intent, [ASSET_CATALOG])
        chunks: list[SourceChunk] = []

        for col_name in collections:
            col = self._get_collection(col_name)

            if col_name == QUOTA_METRICS:
                result = col.get()
                for doc in result.get("documents") or []:
                    chunks.append(SourceChunk(collection=col_name, content=doc, score=1.0))
                continue

            conditions: list[dict[str, object]] = []
            if col_name == ASSET_CATALOG:
                if project:
                    conditions.append({"project_id": {"$eq": project}})
                if dataset:
                    conditions.append({"dataset_id": {"$eq": dataset}})
            elif col_name == QUERY_HISTORY:
                if project:
                    conditions.append({"project_id": {"$eq": project}})
                if user_email:
                    conditions.append({"user_email": {"$eq": user_email}})
                cutoff = _parse_cutoff(time_range)
                if cutoff:
                    conditions.append({"creation_time": {"$gte": cutoff}})

            where = _build_where(conditions)
            n = min(self._n_results, col.count())
            if n == 0:
                continue

            result = col.query(query_texts=[query], n_results=n, where=where)  # type: ignore[arg-type]
            docs = (result.get("documents") or [[]])[0]
            distances = (result.get("distances") or [[]])[0]
            for doc, dist in zip(docs, distances, strict=True):
                chunks.append(SourceChunk(collection=col_name, content=doc, score=1.0 - dist))

        return chunks
