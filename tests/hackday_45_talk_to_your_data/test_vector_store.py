from datetime import UTC, datetime
from pathlib import Path
from typing import cast

import chromadb
import pytest
from chromadb.api.types import Documents, Embeddings
from chromadb.api.types import EmbeddingFunction as ChromaEmbeddingFunction

from hackday_45_talk_to_your_data.vector_store import (
    ASSET_CATALOG,
    COLLECTION_NAMES,
    ChromaDocument,
    create_client,
    create_collections,
    document_from_row,
    upsert_documents,
)


class TestEmbeddingFunction(ChromaEmbeddingFunction[Documents]):
    def __call__(self, input: Documents) -> Embeddings:
        return cast(Embeddings, [[float(len(text)), float(sum(map(ord, text)) % 100)] for text in input])

    @staticmethod
    def name() -> str:
        return "test-embedding"


def test_create_client_uses_persistent_storage(tmp_path: Path) -> None:
    client = create_client(tmp_path / "chroma_db")
    collection = client.get_or_create_collection("persistent_test")
    assert collection.count() == 0


def test_create_collections_uses_default_embedding_function_when_none_provided(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "hackday_45_talk_to_your_data.vector_store.SentenceTransformerEmbeddingFunction",
        TestEmbeddingFunction,
    )

    collections = create_collections(chromadb.EphemeralClient())

    assert set(collections) == set(COLLECTION_NAMES)


def test_document_from_row_maps_document_id_and_text_and_coerces_metadata() -> None:
    document = document_from_row(
        {
            "document_id": "asset:analytics.sales.orders",
            "collection_name": "bq_asset_catalog",
            "document_text": "BigQuery asset: analytics.sales.orders",
            "project_id": "analytics",
            "dataset_id": "sales",
            "creation_time": datetime(2026, 9, 8, 0, 0, 0, tzinfo=UTC),
            "extracted_at": datetime(2026, 9, 8, 1, 0, 0, tzinfo=UTC),
        }
    )

    assert document.record_id == "asset:analytics.sales.orders"
    assert document.document == "BigQuery asset: analytics.sales.orders"
    assert document.metadata["project_id"] == "analytics"
    assert document.metadata["collection_name"] == "bq_asset_catalog"
    assert document.metadata["creation_time"] == datetime(2026, 9, 8, 0, 0, 0, tzinfo=UTC).timestamp()


def test_upsert_documents_creates_filterable_asset_catalog_records() -> None:
    collections = create_collections(chromadb.EphemeralClient(), TestEmbeddingFunction())
    assert set(collections) == set(COLLECTION_NAMES)

    documents = [
        ChromaDocument(
            record_id="asset:analytics.sales.orders",
            document="BigQuery table analytics.sales.orders containing customer orders.",
            metadata={"project_id": "analytics", "dataset_id": "sales", "owner_email": "data@example.com"},
        ),
        ChromaDocument(
            record_id="asset:analytics.marketing.campaigns",
            document="BigQuery table analytics.marketing.campaigns containing campaign activity.",
            metadata={"project_id": "analytics", "dataset_id": "marketing", "owner_email": "marketing@example.com"},
        ),
    ]

    collection = collections[ASSET_CATALOG]
    assert upsert_documents(collection, documents) == 2
    assert collection.count() == 2

    filtered = collection.get(where={"owner_email": "data@example.com"}, include=["metadatas"])
    assert filtered["ids"] == ["asset:analytics.sales.orders"]
    assert filtered["metadatas"] == [
        {"project_id": "analytics", "dataset_id": "sales", "owner_email": "data@example.com"}
    ]
