from motor.motor_asyncio import AsyncIOMotorDatabase

from app.schemas.auth import User


class UserRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._collection = db["users"]

    async def find_by_username(self, username: str) -> User | None:
        raise NotImplementedError

    async def save(self, user: User) -> None:
        raise NotImplementedError
