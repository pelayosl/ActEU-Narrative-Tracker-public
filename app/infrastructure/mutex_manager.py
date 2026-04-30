from redis.asyncio import Redis


class MutexManager:
    def __init__(self, redis: Redis) -> None:
        self._redis = redis

    async def acquire(self, key: str) -> bool:
        raise NotImplementedError

    async def release(self, key: str) -> None:
        raise NotImplementedError

    async def is_locked(self, key: str) -> bool:
        raise NotImplementedError
