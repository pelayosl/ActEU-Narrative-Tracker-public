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
from datetime import datetime, timezone
from pathlib import Path

from pymongo import MongoClient, UpdateOne

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


def parse_published_time(value):
    """Parse a legacy published_time string into a timezone-aware datetime.

    MongoDB migration documents can contain locale-formatted strings such as
    "dom, 01 oct 2023 17:47:19 +0200". This helper strips weekday labels,
    normalizes month names, and preserves timezone offsets.
    """
    if not isinstance(value, str):
        return value

    normalized = value.strip()
    if not normalized:
        return value

    # Remove weekday prefix if present: "dom, 01 oct 2023..." -> "01 oct 2023..."
    if "," in normalized:
        normalized = normalized.split(",", 1)[1].strip()

    # Support Spanish month abbreviations alongside English.
    month_map = {
        "ene": "jan",
        "feb": "feb",
        "mar": "mar",
        "abr": "apr",
        "may": "may",
        "jun": "jun",
        "jul": "jul",
        "ago": "aug",
        "sep": "sep",
        "oct": "oct",
        "nov": "nov",
        "dic": "dec",
    }
    parts = normalized.split()
    if len(parts) >= 3 and parts[1].lower() in month_map:
        parts[1] = month_map[parts[1].lower()]
        normalized = " ".join(parts)

    try:
        if normalized.endswith("Z"):
            normalized = normalized[:-1] + "+00:00"
        dt = datetime.fromisoformat(normalized)
    except ValueError:
        try:
            dt = datetime.strptime(normalized, "%d %b %Y %H:%M:%S %z")
        except ValueError:
            try:
                dt = datetime.strptime(normalized, "%d %b %Y %H:%M:%S")
                dt = dt.replace(tzinfo=timezone.utc)
            except ValueError:
                return value

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


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

    docs = db.documents.find({"published_time": {"$type": "string"}}, {"published_time": 1})
    ops = []
    skipped = 0

    for doc in docs:
        parsed = parse_published_time(doc["published_time"])
        if isinstance(parsed, datetime):
            ops.append(UpdateOne({"_id": doc["_id"]}, {"$set": {"published_time": parsed}}))
        else:
            skipped += 1
            print(f"  [WARN] Could not parse published_time: {doc['published_time']!r}")

    if ops:
        result = db.documents.bulk_write(ops, ordered=False)
        print(f"Matched: {len(ops)} | Modified: {result.modified_count}")
    else:
        print("No parsable string published_time values found.")

    if skipped:
        print(f"Skipped unparseable documents: {skipped}")

    remaining = db.documents.count_documents({"published_time": {"$type": "string"}})
    print(f"Remaining string published_time: {remaining}")
    print("Done.")

    client.close()


if __name__ == "__main__":
    main()
