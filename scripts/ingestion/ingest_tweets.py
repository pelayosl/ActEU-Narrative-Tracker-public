"""
Tweet ingestion script — ActEU Narrative Tracker
Reads a .ndjson file of raw tweets and outputs a .ndjson file in the database schema format.

Configure INPUT_PATH and OUTPUT_PATH below.
"""

import json
from pathlib import Path
from ingestion import (
    PRESUMED_ISSUE_MAP,
    LANGUAGE_TO_COUNTRY,
    extract_acteu_topic,
    extract_acteu_subtopic,
    extract_sentiment,
    extract_named_entities,
)

# ── Configuration ─────────────────────────────────────────────────────────────
INPUT_PATH = Path("C:\\Users\\pelay\\Documents\\EII\\4º Software\\TFG\\Datasets\\filtered-docs\\tweets\\tweets-es.ndjson")
OUTPUT_PATH = Path("C:\\Users\\pelay\\Documents\\EII\\4º Software\\TFG\\Datasets\\db\\tweets\\tweets-es-db.ndjson")
# ──────────────────────────────────────────────────────────────────────────────



def transform_tweet(raw: dict) -> dict | None:
    """
    Transform a raw tweet into the database document schema.
    Returns None if the document should be skipped (missing critical fields).
    """
    plain_text = raw.get("plain_text", "").strip()
    if not plain_text:
        return None

    author_display = raw.get("author", "").strip()
    author_username = raw.get("author_username", "").strip()
    headline = f"{author_display} (@{author_username})" if author_username else author_display

    language = raw.get("language") or raw.get("language_detected", "")
    country = LANGUAGE_TO_COUNTRY.get(language, language.upper() if language else None)

    annotations = raw.get("annotations", {})

    return {
        "headline": headline,
        "plain_text": plain_text,
        "platform": "twitter",
        "country": country,
        "language": language,
        "published_time": raw.get("published_time"),
        "author": author_username or author_display,
        "acteu_topic": extract_acteu_topic(annotations),
        "subtopics": extract_acteu_subtopic(annotations),
        "named_entities": extract_named_entities(raw),
        "sentiment": extract_sentiment(annotations),
    }


def ingest(input_path: Path, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    processed = 0
    skipped = 0

    with input_path.open("r", encoding="utf-8") as infile, \
         output_path.open("w", encoding="utf-8") as outfile:

        for line_number, line in enumerate(infile, start=1):
            line = line.strip()
            if not line:
                continue

            try:
                raw = json.loads(line)
            except json.JSONDecodeError as e:
                print(f"[WARN] Line {line_number}: JSON parse error — {e}")
                skipped += 1
                continue

            doc = transform_tweet(raw)
            if doc is None:
                print(f"[SKIP] Line {line_number}: missing critical fields")
                skipped += 1
                continue

            outfile.write(json.dumps(doc, ensure_ascii=False) + "\n")
            processed += 1

    print(f"\nDone. Processed: {processed} | Skipped: {skipped}")
    print(f"Output written to: {output_path}")


if __name__ == "__main__":
    ingest(INPUT_PATH, OUTPUT_PATH)