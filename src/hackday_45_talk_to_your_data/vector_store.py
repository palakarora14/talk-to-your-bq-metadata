from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

import chromadb
from chromadb.api import ClientAPI
from chromadb.api.types import Documents
from chromadb.api.types import EmbeddingFunction as ChromaEmbeddingFunction
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

from hackday_45_talk_to_your_data.library.helper import text

ASSET_CATALOG = "bq_asset_catalog"
QUERY_HISTORY = "bq_query_history"
QUOTA_METRICS = "bq_quota_metrics"
COLLECTION_NAMES = (ASSET_CATALOG, QUERY_HISTORY, QUOTA_METRICS)

EmbeddingFunction = ChromaEmbeddingFunction[Documents]


@dataclass(frozen=True)
class ChromaDocument:
    record_id: str
    document: str
    metadata: dict[str, str | int | float | bool]


def _metadata_value(value: Any) -> str | int | float | bool:
    if isinstance(value, bool | int | float):
        return value
    if isinstance(value, datetime):
        return value.timestamp()
    if isinstance(value, date):
        return float(datetime(value.year, value.month, value.day).timestamp())
    return text(value)


def document_from_row(row: dict[str, Any]) -> ChromaDocument:
    """Adapts a BigQuery row already shaped with document_id/document_text (see client.bq.BigQueryClient)."""
    metadata = {
        key: _metadata_value(value) for key, value in row.items() if key not in {"document_id", "document_text"}
    }
    return ChromaDocument(
        record_id=text(row["document_id"]),
        document=text(row["document_text"]),
        metadata=metadata,
    )


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CHROMA_PATH = REPO_ROOT / "chroma_db"


def create_client(storage_path: Path = DEFAULT_CHROMA_PATH) -> ClientAPI:
    storage_path.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(storage_path))


def create_collections(
    client: ClientAPI,
    embedding_function: EmbeddingFunction | None = None,
) -> dict[str, Any]:
    if embedding_function is None:
        embedding_function = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")

    return {
        # chromadb's own EmbeddingFunction[Documents] implementations aren't typed as EmbeddingFunction[Embeddable]
        name: client.get_or_create_collection(
            name=name,
            embedding_function=embedding_function,  # type: ignore[arg-type]
        )
        for name in COLLECTION_NAMES
    }


def upsert_documents(collection: Any, documents: Iterable[ChromaDocument], batch_size: int = 100) -> int:
    batch = list(documents)
    for offset in range(0, len(batch), batch_size):
        chunk = batch[offset : offset + batch_size]
        collection.upsert(
            ids=[document.record_id for document in chunk],
            documents=[document.document for document in chunk],
            metadatas=[document.metadata for document in chunk],
        )
    return len(batch)
