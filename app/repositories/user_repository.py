from pymongo.asynchronous.database import AsyncDatabase

from app.schemas.auth import User


class UserRepository:
    def __init__(self, db: AsyncDatabase) -> None:
        self._collection = db["users"]

    async def find_by_username(self, username: str) -> User | None:
        doc = await self._collection.find_one({"username": username})
        if not doc:
            return None
        return User.model_validate(doc)

    async def save(self, user: User) -> None:
        payload = user.model_dump()
        await self._collection.update_one(
            {"user_id": user.user_id},
            {"$set": payload},
            upsert=True,
        )
