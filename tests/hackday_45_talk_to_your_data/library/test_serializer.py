from pathlib import Path
from typing import cast
from unittest.mock import MagicMock, patch

import chromadb
import pytest
from chromadb.api.types import Documents, Embeddings
from chromadb.api.types import EmbeddingFunction as ChromaEmbeddingFunction

# Stub out client.bq and its transitive dependency src.config.constants before importing
# serializer, since that legacy module requires PYTHONPATH=.
with patch.dict(
    "sys.modules",
    {
        "client": MagicMock(),
        "client.bq": MagicMock(),
        "src": MagicMock(),
        "src.config": MagicMock(),
        "src.config.constants": MagicMock(),
    },
):
    from hackday_45_talk_to_your_data.library import serializer  # noqa: E402
    from hackday_45_talk_to_your_data.library.serializer import ingest_project  # noqa: E402


class TestEmbeddingFunction(ChromaEmbeddingFunction[Documents]):
    def __call__(self, input: Documents) -> Embeddings:
        return cast(Embeddings, [[float(len(text)), float(sum(map(ord, text)) % 100)] for text in input])

    @staticmethod
    def name() -> str:
        return "test-embedding"


def test_ingest_project_upserts_rows_from_big_query_client(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    fake_bq_client = MagicMock()
    fake_bq_client.project_id = "ingest_test_project"
    fake_bq_client.fetch_bq_asset_catalog_metadata.return_value = [
        {
            "document_id": "asset:ingest_test_project.warehouse.shipments",
            "document_text": "asset doc",
            "project_id": "ingest_test_project",
        },
    ]
    fake_bq_client.fetch_bq_query_history.return_value = [
        {
            "document_id": "query:ingest_test_project:job_ingest_1",
            "document_text": "query doc",
            "project_id": "ingest_test_project",
        },
    ]
    fake_bq_client.fetch_bq_quota_metrics.return_value = [
        {
            "document_id": "quota:top-costly-queries-7d",
            "document_text": "quota doc",
            "project_id": "ingest_test_project",
        },
    ]

    monkeypatch.setattr(serializer, "BigQueryClient", lambda: fake_bq_client)
    monkeypatch.setattr(
        serializer,
        "create_client",
        lambda: chromadb.PersistentClient(path=str(tmp_path / "chroma")),
    )

    summary = ingest_project(days=7, embedding_function=TestEmbeddingFunction())

    assert summary == {"assets": 1, "query_jobs": 1, "quota_metrics": 1}
    fake_bq_client.fetch_bq_query_history.assert_called_once_with(days=7)
