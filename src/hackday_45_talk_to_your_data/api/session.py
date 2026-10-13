"""In-memory session history store."""

from collections import defaultdict

# session_id -> list of {"role": "user"|"assistant", "content": str}
_store: dict[str, list[dict[str, str]]] = defaultdict(list)


def get_history(session_id: str) -> list[dict[str, str]]:
    return _store[session_id]


def append(session_id: str, role: str, content: str) -> None:
    _store[session_id].append({"role": role, "content": content})


def clear(session_id: str) -> None:
    _store.pop(session_id, None)
