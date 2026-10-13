"""Tests for FastAPI backend."""

from collections.abc import Generator
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from hackday_45_talk_to_your_data.api import session as sessions
from hackday_45_talk_to_your_data.api.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_sessions() -> Generator[None]:
    sessions._store.clear()  # type: ignore[attr-defined]
    yield
    sessions._store.clear()  # type: ignore[attr-defined]


@pytest.fixture(autouse=True)
def mock_llm() -> Generator[None]:
    with patch("hackday_45_talk_to_your_data.api.main.run_chain", return_value="mocked reply"):
        yield


@pytest.fixture(autouse=True)
def mock_retriever() -> Generator[None]:
    with patch("hackday_45_talk_to_your_data.chains.base.ChromaRetriever.retrieve", return_value=[]):
        yield


def test_health() -> None:
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_chat_returns_reply() -> None:
    resp = client.post(
        "/chat",
        json={"session_id": "s1", "message": "What datasets exist?"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["session_id"] == "s1"
    assert body["reply"] == "mocked reply"


def test_chat_stores_history() -> None:
    client.post("/chat", json={"session_id": "s2", "message": "first message"})
    history = sessions.get_history("s2")
    assert len(history) == 2  # user + assistant
    assert history[0]["role"] == "user"
    assert history[1]["role"] == "assistant"


def test_chat_accumulates_history() -> None:
    for msg in ("hello", "follow up"):
        client.post("/chat", json={"session_id": "s3", "message": msg})
    history = sessions.get_history("s3")
    assert len(history) == 4


def test_clear_session() -> None:
    client.post("/chat", json={"session_id": "s4", "message": "hi"})
    resp = client.delete("/chat/s4")
    assert resp.status_code == 200
    assert sessions.get_history("s4") == []


def test_chat_with_filters() -> None:
    resp = client.post(
        "/chat",
        json={
            "session_id": "s5",
            "message": "cost query",
            "project": "rea-gcp-dp-dev",
            "dataset": "marketing",
            "time_range": "last_7_days",
            "user_email": "test@example.com",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert "sources" in body
    assert isinstance(body["sources"], list)


def test_chat_with_all_projects() -> None:
    resp = client.post(
        "/chat",
        json={"session_id": "s6", "message": "list datasets", "project": None},
    )
    assert resp.status_code == 200
    assert resp.json()["reply"] == "mocked reply"
