"""In-process TTL cache for market heatmap API responses."""

from __future__ import annotations

import time
from threading import Lock

DEFAULT_TTL_SECONDS = 600

_store: dict[str, dict] = {}
_lock = Lock()


def get_cached(key: str, ttl_seconds: int = DEFAULT_TTL_SECONDS):
    now = time.time()
    with _lock:
        entry = _store.get(key)
        if not entry:
            return None
        if now - entry["ts"] > ttl_seconds:
            del _store[key]
            return None
        return entry["value"]


def set_cached(key: str, value) -> None:
    with _lock:
        _store[key] = {"ts": time.time(), "value": value}


def clear_cached(prefix: str | None = None) -> int:
    """Drop cache entries; optional prefix match. Returns number removed."""
    with _lock:
        if prefix is None:
            count = len(_store)
            _store.clear()
            return count
        keys = [key for key in _store if key.startswith(prefix)]
        for key in keys:
            del _store[key]
        return len(keys)
