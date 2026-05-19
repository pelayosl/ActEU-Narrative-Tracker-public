from redis.asyncio import Redis


class MutexManager:
    """Thin Redis-based distributed lock. No business logic."""

    def __init__(self, redis: Redis, default_ttl: int = 600) -> None:
        self._redis = redis
        self._default_ttl = default_ttl

    async def acquire(self, key: str, ttl: int | None = None) -> bool:
        """Atomically acquire the lock. Returns True on success, False if already held."""
        result = await self._redis.set(key, "1", nx=True, ex=ttl or self._default_ttl)
        return bool(result)

    async def release(self, key: str) -> None:
        await self._redis.delete(key)

    async def is_locked(self, key: str) -> bool:
        return bool(await self._redis.exists(key))
