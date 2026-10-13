"""Integration tests for ChromaRetriever using an ephemeral in-memory Chroma client."""

from collections.abc import Generator
from datetime import UTC, datetime, timedelta

import chromadb
import chromadb.api
import pytest
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

from hackday_45_talk_to_your_data.chains.base import ChromaRetriever
from hackday_45_talk_to_your_data.vector_store import ASSET_CATALOG, QUERY_HISTORY, QUOTA_METRICS

_EF = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")

NOW_TS = datetime.now(UTC).timestamp()
OLD_TS = (datetime.now(UTC) - timedelta(days=30)).timestamp()
RECENT_TS = (datetime.now(UTC) - timedelta(days=2)).timestamp()


@pytest.fixture()
def ephemeral_client() -> chromadb.api.ClientAPI:
    return chromadb.EphemeralClient()


@pytest.fixture()
def seeded_client(
    ephemeral_client: chromadb.api.ClientAPI,
) -> Generator[chromadb.api.ClientAPI]:
    for name in [ASSET_CATALOG, QUERY_HISTORY, QUOTA_METRICS]:
        try:
            ephemeral_client.delete_collection(name)
        except Exception:
            pass

    asset_col = ephemeral_client.get_or_create_collection(ASSET_CATALOG, embedding_function=_EF)  # type: ignore[arg-type]
    asset_col.upsert(
        ids=["a1", "a2", "a3"],
        documents=[
            "table foo in project-a dataset ds1",
            "table bar in project-b dataset ds2",
            "table baz in project-a dataset ds2",
        ],
        metadatas=[
            {"project_id": "project-a", "dataset_id": "ds1"},
            {"project_id": "project-b", "dataset_id": "ds2"},
            {"project_id": "project-a", "dataset_id": "ds2"},
        ],
    )

    qh_col = ephemeral_client.get_or_create_collection(QUERY_HISTORY, embedding_function=_EF)  # type: ignore[arg-type]
    qh_col.upsert(
        ids=["q1", "q2", "q3"],
        documents=[
            "SELECT * FROM foo -- user alice recent",
            "SELECT * FROM bar -- user bob old",
            "SELECT * FROM baz -- user alice old",
        ],
        metadatas=[
            {"project_id": "project-a", "user_email": "alice@example.com", "creation_time": RECENT_TS},
            {"project_id": "project-a", "user_email": "bob@example.com", "creation_time": OLD_TS},
            {"project_id": "project-a", "user_email": "alice@example.com", "creation_time": OLD_TS},
        ],
    )

    quota_col = ephemeral_client.get_or_create_collection(QUOTA_METRICS, embedding_function=_EF)  # type: ignore[arg-type]
    quota_col.upsert(
        ids=["m1", "m2"],
        documents=["quota summary A", "quota summary B"],
        metadatas=[
            {"metric_type": "slot_usage", "metric_time": NOW_TS},
            {"metric_type": "byte_usage", "metric_time": NOW_TS},
        ],
    )

    yield ephemeral_client

    for name in [ASSET_CATALOG, QUERY_HISTORY, QUOTA_METRICS]:
        try:
            ephemeral_client.delete_collection(name)
        except Exception:
            pass


def test_project_filter_narrows_asset_results(seeded_client: chromadb.api.ClientAPI) -> None:
    r = ChromaRetriever.from_client(seeded_client, _EF)
    chunks = r.retrieve("table", "asset", "project-a", None, None)
    assert all(c.collection == ASSET_CATALOG for c in chunks)
    assert len(chunks) == 2  # a1, a3


def test_user_email_filter_narrows_query_history(seeded_client: chromadb.api.ClientAPI) -> None:
    r = ChromaRetriever.from_client(seeded_client, _EF)
    chunks = r.retrieve("SELECT", "cost", None, None, None, user_email="bob@example.com")
    qh_chunks = [c for c in chunks if c.collection == QUERY_HISTORY]
    assert len(qh_chunks) == 1
    assert "bob" in qh_chunks[0].content


def test_all_time_returns_all_query_history_docs(seeded_client: chromadb.api.ClientAPI) -> None:
    r = ChromaRetriever.from_client(seeded_client, _EF)
    chunks = r.retrieve("SELECT", "cost", "project-a", None, "all_time")
    qh_chunks = [c for c in chunks if c.collection == QUERY_HISTORY]
    assert len(qh_chunks) == 3


def test_last_7_days_excludes_old_docs(seeded_client: chromadb.api.ClientAPI) -> None:
    r = ChromaRetriever.from_client(seeded_client, _EF)
    chunks = r.retrieve("SELECT", "cost", "project-a", None, "last_7_days")
    qh_chunks = [c for c in chunks if c.collection == QUERY_HISTORY]
    assert len(qh_chunks) == 1
    assert "alice" in qh_chunks[0].content


def test_quota_metrics_always_returns_all(seeded_client: chromadb.api.ClientAPI) -> None:
    r = ChromaRetriever.from_client(seeded_client, _EF)
    chunks = r.retrieve("quota", "cost", "some-other-project", "other-dataset", "last_1_day")
    quota_chunks = [c for c in chunks if c.collection == QUOTA_METRICS]
    assert len(quota_chunks) == 2


def test_n_results_capped_at_collection_count(seeded_client: chromadb.api.ClientAPI) -> None:
    r = ChromaRetriever.from_client(seeded_client, _EF, n_results=100)
    chunks = r.retrieve("table", "asset", None, None, None)
    assert len(chunks) == 3
