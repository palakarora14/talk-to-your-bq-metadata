"""Tests for chain intent routing, session helpers, and reranker."""

import pytest

from hackday_45_talk_to_your_data.api import session as sessions
from hackday_45_talk_to_your_data.api.models import SourceChunk
from hackday_45_talk_to_your_data.chains.base import INTENT_COLLECTIONS, MockRetriever
from hackday_45_talk_to_your_data.chains.chains import detect_intent, run_chain
from hackday_45_talk_to_your_data.chains.reranker import rerank


def test_intent_cost() -> None:
    assert detect_intent("What are the costliest queries?") == "cost"


def test_intent_optimise() -> None:
    assert detect_intent("Which tables are not partitioned?") == "optimise"


def test_intent_asset_default() -> None:
    assert detect_intent("List all datasets") == "asset"


def test_mock_retriever_asset_collections() -> None:
    r = MockRetriever()
    chunks = r.retrieve("show tables", "asset", None, None, None)
    assert len(chunks) == len(INTENT_COLLECTIONS["asset"])
    assert all(c.collection == "bq_asset_catalog" for c in chunks)


def test_mock_retriever_cost_collections() -> None:
    r = MockRetriever()
    chunks = r.retrieve("expensive queries", "cost", "rea-gcp-dp-dev", None, None)
    assert len(chunks) == len(INTENT_COLLECTIONS["cost"])
    assert any(c.collection == "bq_query_history" for c in chunks)
    assert any(c.collection == "bq_quota_metrics" for c in chunks)


def test_mock_retriever_optimise_collections() -> None:
    r = MockRetriever()
    chunks = r.retrieve("partition tables", "optimise", None, None, None)
    assert len(chunks) == len(INTENT_COLLECTIONS["optimise"])


def test_mock_retriever_includes_project_in_chunk() -> None:
    r = MockRetriever()
    chunks = r.retrieve("query", "asset", "rea-gcp-dp-dev", None, None)
    assert all("project='rea-gcp-dp-dev'" in c.content for c in chunks)


def test_mock_retriever_all_projects_passes_none() -> None:
    r = MockRetriever()
    chunks = r.retrieve("query", "asset", None, None, None)
    assert all("project=None" in c.content for c in chunks)


def test_rerank_passthrough_when_under_top_n() -> None:
    chunks = [SourceChunk(collection="c", content=f"chunk {i}", score=1.0) for i in range(2)]
    assert rerank("query", chunks) == chunks


def test_rerank_trims_to_top_n() -> None:
    chunks = [SourceChunk(collection="c", content=f"chunk {i}", score=1.0) for i in range(20)]
    result = rerank("query", chunks, top_n=5)
    assert len(result) == 5
    assert all(isinstance(r, SourceChunk) for r in result)


def test_session_append_and_get() -> None:
    sessions._store.clear()  # type: ignore[attr-defined]
    sessions.append("x", "user", "hello")
    sessions.append("x", "assistant", "hi")
    h = sessions.get_history("x")
    assert h == [{"role": "user", "content": "hello"}, {"role": "assistant", "content": "hi"}]


def test_session_clear() -> None:
    sessions._store.clear()  # type: ignore[attr-defined]
    sessions.append("y", "user", "msg")
    sessions.clear("y")
    assert sessions.get_history("y") == []


def test_run_chain_no_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("PORTKEY_API_KEY", raising=False)
    result = run_chain("hello", [SourceChunk(collection="c", content="ctx chunk", score=1.0)], [])
    assert "LLM not configured" in result
    assert "ctx chunk" in result
