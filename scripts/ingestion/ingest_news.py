"""
News ingestion script — ActEU Narrative Tracker
Traverses a directory of .ndjson files (one per domain) and outputs a single
.ndjson file in the database schema format.


Configure INPUT_DIR and OUTPUT_PATH below.
"""

import json
import re
from pathlib import Path
from ingestion import (
    PRESUMED_ISSUE_MAP,
    LANGUAGE_TO_COUNTRY,
    extract_acteu_topic,
    extract_sentiment,
    extract_named_entities,
)

# ── Configuration ─────────────────────────────────────────────────────────────
INPUT_DIR = Path("C:\\Users\\pelay\\Documents\\EII\\4º Software\\TFG\\Datasets\\filtered-docs\\news\\es")
OUTPUT_PATH = Path("C:\\Users\\pelay\\Documents\\EII\\4º Software\\TFG\\Datasets\\db\\news\\news-es-db.ndjson")
# ──────────────────────────────────────────────────────────────────────────────



def transform_news(raw: dict) -> dict | None:
    clean_text = raw.get("clean_text", "").strip()
    if not clean_text:
        return None

    headline = raw.get("title") or raw.get("description") or ""
    if isinstance(headline, list):
        headline = headline[0] if headline else ""
    headline = headline.strip()

    author = raw.get("site_name", "").strip()
    language = raw.get("language_detected", "")
    country = LANGUAGE_TO_COUNTRY.get(language, language.upper() if language else None)

    annotations = raw.get("annotations", {})

    return {
        "headline": headline,
        "plain_text": clean_text,
        "platform": "media",
        "country": country,
        "language": language,
        "published_time": raw.get("published_time"),
        "author": author,
        "acteu_topic": extract_acteu_topic(annotations),
        "subtopics": [],
        "named_entities": extract_named_entities(raw),
        "sentiment": extract_sentiment(annotations),
    }


def ingest(input_dir: Path, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    ndjson_files = sorted(input_dir.glob("*.ndjson"))
    if not ndjson_files:
        print(f"[WARN] No .ndjson files found in {input_dir}")
        return

    print(f"Found {len(ndjson_files)} file(s) to process.")

    total_processed = 0
    total_skipped = 0

    with output_path.open("w", encoding="utf-8") as outfile:
        for filepath in ndjson_files:
            print(f"Processing: {filepath.name}")
            file_processed = 0
            file_skipped = 0

            with filepath.open("r", encoding="utf-8") as infile:
                for line_number, line in enumerate(infile, start=1):
                    line = line.strip()
                    if not line:
                        continue

                    try:
                        raw = json.loads(line)
                    except json.JSONDecodeError as e:
                        print(f"  [WARN] Line {line_number}: JSON parse error — {e}")
                        file_skipped += 1
                        continue

                    doc = transform_news(raw)
                    if doc is None:
                        print(f"  [SKIP] Line {line_number}: missing critical fields")
                        file_skipped += 1
                        continue

                    outfile.write(json.dumps(doc, ensure_ascii=False) + "\n")
                    file_processed += 1

            print(f"  → Processed: {file_processed} | Skipped: {file_skipped}")
            total_processed += file_processed
            total_skipped += file_skipped

    print(f"\nDone. Total processed: {total_processed} | Total skipped: {total_skipped}")
    print(f"Output written to: {output_path}")


if __name__ == "__main__":
    ingest(INPUT_DIR, OUTPUT_PATH)