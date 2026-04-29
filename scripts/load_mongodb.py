"""
MongoDB loader script — ActEU Narrative Tracker
Reads transformed ndjson files organised by platform/country and bulk-inserts
them into MongoDB. Also seeds the topics collection with the three core topics.

Assumes a clean database — does NOT skip duplicates.

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
import uuid
from datetime import datetime, timezone
from pathlib import Path

from pymongo import MongoClient

# ── Configuration ─────────────────────────────────────────────────────────────
MONGO_URI = "mongodb://localhost:27017"
DB_NAME = "acteu_dev"
DATA_DIR = Path("C:\\Users\\pelay\\Documents\\EII\\4º Software\\TFG\\Datasets\\db")
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

                doc.pop("subtopics", None)  # subtopics live in project document_proxies, not in documents
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


def main() -> None:
    client = MongoClient(MONGO_URI)
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
    create_indexes(db)

    print(f"\n{'='*40}")
    print(f"Total documents inserted: {grand_total_inserted}")
    print(f"Total documents skipped:  {grand_total_skipped}")
    print(f"{'='*40}")

    client.close()


if __name__ == "__main__":
    main()