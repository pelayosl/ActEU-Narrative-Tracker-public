from pymongo.asynchronous.database import AsyncDatabase

from app.schemas.auth import User


class UserRepository:
    """Data-access layer for the ``users`` collection.

    Persists and retrieves :class:`User` entities. Used only by the service layer
    (``AuthService``), never imported directly by the API gateway or tasks.
    """

    def __init__(self, db: AsyncDatabase) -> None:
        """Bind the repository to the ``users`` collection of the given database.

        :param db: The async MongoDB database handle.
        """
        self._collection = db["users"]

    async def find_by_username(self, username: str) -> User | None:
        """Look up a single user by their unique username.

        :param username: The username to search for.
        :returns: The matching :class:`User`, or ``None`` if no user exists.
        """
        doc = await self._collection.find_one({"username": username})
        if not doc:
            return None
        return User.model_validate(doc)

    async def save(self, user: User) -> None:
        """Insert or update a user, upserting by ``user_id``.

        :param user: The user entity to persist.
        """
        payload = user.model_dump()
        await self._collection.update_one(
            {"user_id": user.user_id},
            {"$set": payload},
            upsert=True,
        )
