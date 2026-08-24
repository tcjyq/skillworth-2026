from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from skillworth_api.cache import TTLCache


def test_cache_returns_hits_for_repeated_keys() -> None:
    cache = TTLCache(60)

    first = cache.get_or_load("same", lambda: "value")
    second = cache.get_or_load("same", lambda: "different")

    assert first.value == "value"
    assert first.hit is False
    assert second.value == "value"
    assert second.hit is True


def test_cache_does_not_serialize_loaders_for_unrelated_keys() -> None:
    cache = TTLCache(60)
    barrier = Barrier(2)

    def load(value: str) -> str:
        barrier.wait(timeout=2)
        return value

    with ThreadPoolExecutor(max_workers=2) as executor:
        left = executor.submit(cache.get_or_load, "left", lambda: load("left"))
        right = executor.submit(cache.get_or_load, "right", lambda: load("right"))

        assert left.result(timeout=3).value == "left"
        assert right.result(timeout=3).value == "right"
