"""Fixed-window rate limiting backed by Redis, so limits hold across API processes."""

from functools import lru_cache
from typing import Protocol

import redis

from app.core.config import get_settings


class Limiter(Protocol):
    def hit(self, key: str, limit: int, window_seconds: int) -> bool:
        """Record one hit. Return True if the caller is still within the limit."""
        ...


class RedisLimiter:
    def __init__(self, client: "redis.Redis") -> None:
        self._client = client

    def hit(self, key: str, limit: int, window_seconds: int) -> bool:
        full_key = f"ratelimit:{key}"
        pipe = self._client.pipeline()
        pipe.incr(full_key)
        pipe.expire(full_key, window_seconds, nx=True)
        results = pipe.execute()  # type: ignore[no-untyped-call]
        count = results[0]
        return int(count) <= limit


class MemoryLimiter:
    """For tests only. Not shared across processes."""

    def __init__(self) -> None:
        self.counts: dict[str, int] = {}

    def hit(self, key: str, limit: int, window_seconds: int) -> bool:
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key] <= limit


@lru_cache
def get_limiter() -> Limiter:
    return RedisLimiter(redis.Redis.from_url(get_settings().redis_url))
