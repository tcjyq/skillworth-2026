from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from threading import RLock
from time import monotonic
from typing import Generic, TypeVar


T = TypeVar("T")


@dataclass(frozen=True)
class CacheLookup(Generic[T]):
    value: T
    hit: bool


class TTLCache:
    """Small process-local cache for repeatable read-only warehouse queries."""

    def __init__(self, ttl_seconds: float) -> None:
        if ttl_seconds <= 0:
            raise ValueError("ttl_seconds must be positive")
        self._ttl_seconds = ttl_seconds
        self._entries: dict[str, tuple[float, object]] = {}
        self._lock = RLock()

    def get_or_load(self, key: str, loader: Callable[[], T]) -> CacheLookup[T]:
        with self._lock:
            entry = self._entries.get(key)
            if entry is not None and entry[0] > monotonic():
                return CacheLookup(value=entry[1], hit=True)  # type: ignore[arg-type]

        # DuckDB reads can be comparatively expensive. Do not serialize unrelated
        # cache keys behind the process-wide lock while their loaders are running.
        value = loader()
        with self._lock:
            entry = self._entries.get(key)
            if entry is not None and entry[0] > monotonic():
                return CacheLookup(value=entry[1], hit=True)  # type: ignore[arg-type]
            self._entries[key] = (monotonic() + self._ttl_seconds, value)
            return CacheLookup(value=value, hit=False)
