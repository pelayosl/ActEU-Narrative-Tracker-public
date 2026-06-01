"""
One-time migration — ActEU Narrative Tracker

Converts `documents.published_time` values that were stored as ISO-8601 *strings*
into proper BSON `Date` values, so date-range queries ($gte/$lte against datetimes)
match. String and Date are distinct BSON types in MongoDB; a datetime comparison
never matches a string-typed field, which silently emptied search and visualisation
date filters.

Idempotent: only documents whose `published_time` is currently a string are touched.
Documents with a null/missing/already-Date `published_time` are left untouched.

Usage:
    python scripts/migrate_published_time.py
"""

import os
from pathlib import Path

from pymongo import MongoClient

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
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def main() -> None:
    load_env_file(ENV_PATH)
    mongo_uri = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    db_name = os.getenv("MONGODB_DB", "acteu_dev")

    client = MongoClient(mongo_uri)
    db = client[db_name]

    string_count = db.documents.count_documents({"published_time": {"$type": "string"}})
    print(f"Database: {db_name}")
    print(f"Documents with string published_time: {string_count}")

    if string_count == 0:
        print("Nothing to migrate.")
        client.close()
        return

    # Server-side conversion via aggregation-pipeline update. $toDate parses ISO-8601
    # strings (naive timestamps are interpreted as UTC).
    result = db.documents.update_many(
        {"published_time": {"$type": "string"}},
        [{"$set": {"published_time": {"$toDate": "$published_time"}}}],
    )
    print(f"Matched: {result.matched_count} | Modified: {result.modified_count}")

    remaining = db.documents.count_documents({"published_time": {"$type": "string"}})
    print(f"Remaining string published_time: {remaining}")
    print("Done.")

    client.close()


if __name__ == "__main__":
    main()
