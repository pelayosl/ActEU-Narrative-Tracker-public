from motor.motor_asyncio import AsyncIOMotorDatabase

from app.schemas.auth import User


class UserRepository:
    def __init__(self, db: AsyncIOMotorDatabase) -> None:
        self._collection = db["users"]

    async def find_by_username(self, username: str) -> User | None:
        doc = await self._collection.find_one({"username": username})
        if not doc:
            return None
        if "hashed_password" in doc:
            doc["hashed_pswd"] = doc.pop("hashed_password")
        return User.model_validate(doc)

    async def save(self, user: User) -> None:
        payload = user.model_dump()
        payload["hashed_password"] = payload.pop("hashed_pswd")
        await self._collection.update_one(
            {"user_id": user.user_id},
            {"$set": payload},
            upsert=True,
        )
