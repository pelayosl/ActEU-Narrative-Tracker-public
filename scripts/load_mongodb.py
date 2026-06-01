"""
MongoDB loader script — ActEU Narrative Tracker
Reads transformed ndjson files organised by platform/country and bulk-inserts
them into MongoDB. Also seeds the topics collection with the three core topics,
an admin user, and a starter project.

This script DROPS the target database before loading.

Directory structure expected:
    DATA_DIR/
    ├── tweets/
    │   ├── es.ndjson
    │   └── fi.ndjson
    ├── telegram/
    │   ├── es.ndjson
    │   └── fi.ndjson
    └── news/
        ├── es.ndjson
        └── fi.ndjson

Usage:
    python load_mongodb.py
"""

import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Ensure project root is on sys.path when running this script directly
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from pymongo import MongoClient
from app.infrastructure.password_hasher import PasswordHasher

ENV_PATH = Path(".env")


def load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue

        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip("\"").strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


load_env_file(ENV_PATH)

# ── Configuration ─────────────────────────────────────────────────────────────
MONGO_URI = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DB_NAME = os.getenv("MONGODB_DB", "acteu_dev")
DATA_DIR = Path(
    os.getenv("DATA_DIR", "C:\\Users\\pelay\\Documents\\EII\\4º Software\\TFG\\Datasets\\db")
)
BATCH_SIZE = 500  # documents per bulk insert
# ──────────────────────────────────────────────────────────────────────────────

PLATFORM_DIRS = ["tweets", "telegram", "news"]

CORE_TOPICS = [
    {
        "topic_id": str(uuid.uuid4()),
        "name": "Immigration",
        "description": "Documents related to immigration, migration and border policies in Europe.",
        "core_topic": "immigration",
        "created_at": datetime.now(timezone.utc),
    },
    {
        "topic_id": str(uuid.uuid4()),
        "name": "Climate Change",
        "description": "Documents related to climate change, environmental policy and sustainability.",
        "core_topic": "climate_change",
        "created_at": datetime.now(timezone.utc),
    },
    {
        "topic_id": str(uuid.uuid4()),
        "name": "Gender Issues",
        "description": "Documents related to gender issues, equality and related policies.",
        "core_topic": "gender_issues",
        "created_at": datetime.now(timezone.utc),
    },
]

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_NAME = os.getenv("ADMIN_NAME", "Admin")
ADMIN_SURNAME = os.getenv("ADMIN_SURNAME", "User")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
ADMIN_PROJECT_NAME = os.getenv("ADMIN_PROJECT_NAME", "Default Project")


def parse_published_time(value):
    """Parse an ISO-8601 published_time string into a datetime so it is stored as a
    BSON Date (not a string). Naive timestamps are treated as UTC. Returns the value
    unchanged if it is missing or unparseable."""
    if not isinstance(value, str):
        return value
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return value
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def load_platform_dir(platform_dir: Path, collection) -> tuple[int, int]:
    """
    Load all ndjson files in a platform directory into the given collection.
    Returns (total_inserted, total_skipped).
    """
    ndjson_files = sorted(platform_dir.glob("*.ndjson"))
    if not ndjson_files:
        print(f"  [WARN] No .ndjson files found in {platform_dir}")
        return 0, 0

    total_inserted = 0
    total_skipped = 0

    for filepath in ndjson_files:
        print(f"  Loading: {filepath.name}")
        batch = []
        file_inserted = 0
        file_skipped = 0

        with filepath.open("r", encoding="utf-8") as f:
            for line_number, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue

                try:
                    doc = json.loads(line)
                except json.JSONDecodeError as e:
                    print(f"    [WARN] Line {line_number}: JSON parse error — {e}")
                    file_skipped += 1
                    continue

                doc["subtopics"] = doc.get("subtopics", [])
                doc["published_time"] = parse_published_time(doc.get("published_time"))
                batch.append(doc)

                if len(batch) >= BATCH_SIZE:
                    collection.insert_many(batch, ordered=False)
                    file_inserted += len(batch)
                    batch = []

        # Insert remaining documents
        if batch:
            collection.insert_many(batch, ordered=False)
            file_inserted += len(batch)

        print(f"    → Inserted: {file_inserted} | Skipped: {file_skipped}")
        total_inserted += file_inserted
        total_skipped += file_skipped

    return total_inserted, total_skipped


def create_indexes(db) -> None:
    print("\nCreating indexes...")
    db.documents.create_index("platform")
    db.documents.create_index("country")
    db.documents.create_index("published_time")
    db.documents.create_index("acteu_topic.label")
    db.topics.create_index("topic_id", unique=True)
    db.users.create_index("username", unique=True)
    db.projects.create_index("project_id", unique=True)
    db.projects.create_index("owner_id")
    print("Indexes created.")


def seed_core_topics(db) -> None:
    print("\nSeeding core topics...")
    db.topics.insert_many(CORE_TOPICS)
    print(f"  → Inserted {len(CORE_TOPICS)} core topics.")


def seed_admin_and_project(db) -> None:
    if not ADMIN_PASSWORD:
        raise ValueError("ADMIN_PASSWORD is required (set it in .env or env vars).")

    hasher = PasswordHasher()
    user_id = str(uuid.uuid4())
    project_id = str(uuid.uuid4())

    admin_user = {
        "user_id": user_id,
        "name": ADMIN_NAME,
        "surname": ADMIN_SURNAME,
        "username": ADMIN_USERNAME,
        "hashed_password": hasher.hash(ADMIN_PASSWORD),
        "role": "admin",
    }

    project = {
        "project_id": project_id,
        "owner_id": user_id,
        "name": ADMIN_PROJECT_NAME,
        "created_at": datetime.now(timezone.utc),
        "classifiers": [],
        "document_proxies": [],
    }

    print("\nSeeding admin user and starter project...")
    db.users.insert_one(admin_user)
    db.projects.insert_one(project)
    print("  → Inserted admin user and project.")


def main() -> None:
    client = MongoClient(MONGO_URI)

    print(f"Dropping database: {DB_NAME}")
    client.drop_database(DB_NAME)
    db = client[DB_NAME]

    print(f"Connected to MongoDB: {MONGO_URI}")
    print(f"Database: {DB_NAME}\n")

    grand_total_inserted = 0
    grand_total_skipped = 0

    for platform in PLATFORM_DIRS:
        platform_dir = DATA_DIR / platform
        if not platform_dir.exists():
            print(f"[WARN] Directory not found, skipping: {platform_dir}")
            continue

        print(f"--- Platform: {platform} ---")
        inserted, skipped = load_platform_dir(platform_dir, db.documents)
        grand_total_inserted += inserted
        grand_total_skipped += skipped

    seed_core_topics(db)
    seed_admin_and_project(db)
    create_indexes(db)

    print(f"\n{'='*40}")
    print(f"Total documents inserted: {grand_total_inserted}")
    print(f"Total documents skipped:  {grand_total_skipped}")
    print(f"{'='*40}")

    client.close()


if __name__ == "__main__":
    main()