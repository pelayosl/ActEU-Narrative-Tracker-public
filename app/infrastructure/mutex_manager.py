from redis.asyncio import Redis


class MutexManager:
    """Thin Redis-based distributed lock with no business logic.

    Used by Phase 2 labelling to allow at most one job per project at a time. Locks
    carry a TTL so a crashed holder cannot block a project forever.
    """

    def __init__(self, redis: Redis, default_ttl: int = 600) -> None:
        """Store the Redis client and default lock lifetime.

        :param redis: An async Redis client.
        :param default_ttl: Default lock expiry in seconds when none is given on acquire.
        """
        self._redis = redis
        self._default_ttl = default_ttl

    async def acquire(self, key: str, ttl: int | None = None) -> bool:
        """Atomically acquire a lock if it is free.

        :param key: The lock key.
        :param ttl: Optional expiry in seconds, falling back to the default.
        :returns: ``True`` on success, ``False`` if the lock is already held.
        """
        result = await self._redis.set(key, "1", nx=True, ex=ttl or self._default_ttl)
        return bool(result)

    async def release(self, key: str) -> None:
        """Release a held lock, deleting its key.

        :param key: The lock key to release.
        """
        await self._redis.delete(key)

    async def is_locked(self, key: str) -> bool:
        """Report whether a lock is currently held.

        :param key: The lock key to check.
        :returns: ``True`` if the key exists, ``False`` otherwise.
        """
        return bool(await self._redis.exists(key))
