import time
from typing import Any

_DEFAULT_TTL = 300  # 5 minutes

_store: dict[str, tuple[float, Any]] = {}


def get(key: str) -> Any | None:
    entry = _store.get(key)
    if entry is None:
        return None
    expires_at, value = entry
    if time.monotonic() > expires_at:
        _store.pop(key, None)
        return None
    return value


def set(key: str, value: Any, ttl: int = _DEFAULT_TTL) -> None:
    _store[key] = (time.monotonic() + ttl, value)


def invalidate(key: str | None = None) -> None:
    if key is None:
        _store.clear()
    else:
        _store.pop(key, None)
