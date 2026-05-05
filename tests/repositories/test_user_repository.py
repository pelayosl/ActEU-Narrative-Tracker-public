import pytest

from app.repositories.user_repository import UserRepository
from app.schemas.auth import User


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_user(**overrides) -> User:
	base = {
		"user_id": "user-123",
		"name": "Ana",
		"surname": "Lopez",
		"username": "alopez",
		"hashed_pswd": "hashed-secret",
		"role": "user",
	}
	base.update(overrides)
	return User(**base)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
async def repo(db):
	return UserRepository(db)


# ---------------------------------------------------------------------------
# find_by_username()
# ---------------------------------------------------------------------------

class TestFindByUsername:
	async def test_returns_none_when_missing(self, repo):
		'''
		Checks that searching for a non-existent username returns None
		'''
		result = await repo.find_by_username("missing")
		assert result is None

	async def test_maps_hashed_password_field(self, db, repo):
		'''
		Inserts a user with a hashed_password field and verifies that the repository 
		correctly maps it to the hashed_pswd attribute in the returned User object.
		'''
		payload = {
			"user_id": "user-1",
			"name": "Luis",
			"surname": "Garcia",
			"username": "lgarcia",
			"hashed_password": "hashed-1",
			"role": "admin",
		}
		await db["users"].insert_one(payload)

		result = await repo.find_by_username("lgarcia")

		assert result is not None
		assert result.user_id == "user-1"
		assert result.name == "Luis"
		assert result.surname == "Garcia"
		assert result.username == "lgarcia"
		assert result.hashed_pswd == "hashed-1"
		assert result.role == "admin"


# ---------------------------------------------------------------------------
# save()
# ---------------------------------------------------------------------------

class TestSave:
	async def test_inserts_document_with_hashed_password(self, db, repo):
		'''
		Saves a new user and checks that all fields are correctly stored 
		in the database, with hashed_pswd mapped to hashed_password.
		'''
		user = make_user()

		await repo.save(user)

		doc = await db["users"].find_one({"user_id": user.user_id})
		assert doc is not None
		assert doc["user_id"] == user.user_id
		assert doc["name"] == user.name
		assert doc["surname"] == user.surname
		assert doc["username"] == user.username
		assert doc["hashed_password"] == user.hashed_pswd
		assert "hashed_pswd" not in doc
		assert doc["role"] == user.role

	async def test_updates_existing_document_by_user_id(self, db, repo):
		'''
		Saves a user, then saves another user with the same user_id but 
		different data, and checks that the document is updated (not duplicated) 
		and all fields reflect the new data.
		'''
		original = make_user()
		await repo.save(original)

		updated = make_user(
			name="Maria",
			surname="Santos",
			username="msantos",
			hashed_pswd="hashed-updated",
			role="admin",
		)
		await repo.save(updated)

		docs = await db["users"].find({"user_id": original.user_id}).to_list(length=10)
		assert len(docs) == 1
		doc = docs[0]
		assert doc["name"] == "Maria"
		assert doc["surname"] == "Santos"
		assert doc["username"] == "msantos"
		assert doc["hashed_password"] == "hashed-updated"
		assert doc["role"] == "admin"
