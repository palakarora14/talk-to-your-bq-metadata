from json import dumps
from typing import Any


def text(value: Any, default: str = "") -> str:
    return default if value is None else str(value)


def json_text(value: Any, default: str = "{}") -> str:
    if value is None:
        return default
    if isinstance(value, str):
        return value
    return dumps(value, sort_keys=True, default=str)


def int_value(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def float_value(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
