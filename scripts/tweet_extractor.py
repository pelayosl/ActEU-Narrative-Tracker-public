"""
Tweet ingestion script — ActEU Narrative Tracker
Reads a .ndjson file of raw tweets and outputs a .ndjson file in the database schema format.

Usage:
    python ingest_tweets.py

Configure INPUT_PATH and OUTPUT_PATH below.
"""

import json
import re
from pathlib import Path

# ── Configuration ─────────────────────────────────────────────────────────────
INPUT_PATH = Path("...")
OUTPUT_PATH = Path("...")
# ──────────────────────────────────────────────────────────────────────────────

# Map PresumedIssue labels to normalised core topic names
PRESUMED_ISSUE_MAP = {
    "Migration": "immigration",
    "Climate": "climate_change",
    "Gender": "gender_issues",
}

# Derive country code from language
# TEMPORAL
LANGUAGE_TO_COUNTRY = {
    "es": "ES",
    "fi": "FI",
    "fr": "FR",
    "de": "DE",
    "it": "IT",
    "pl": "PL",
    "nl": "NL",
    "sv": "SE",
    "hu": "HU",
    "pt": "PT",
    "el": "GR",
}


def extract_acteu_topic(annotations: dict) -> dict | None:
    """
    Derive the core topic label from annotations.PresumedIssue.
    Picks the highest confidence entry. Returns None if no core topic matched.
    """
    presumed_issue = annotations.get("PresumedIssue", {})
    if not presumed_issue:
        return None

    best_label, best_confidence = max(presumed_issue.items(), key=lambda x: x[1])
    normalised = PRESUMED_ISSUE_MAP.get(best_label)
    if not normalised:
        return None

    return {"label": normalised, "confidence": best_confidence}


def extract_sentiment(annotations: dict) -> str | None:
    """
    Derive a single sentiment label from GeneralTone.
    - If only one label present, use it directly.
    - If multiple, pick the highest only.
    """
    general_tone = annotations.get("GeneralTone", {})
    if not general_tone:
        return None

    normalise = {
        "Positive": "positive",
        "Negative": "negative",
        "Neutral": "neutral",
    }

    entries = [(normalise.get(k, k.lower()), v) for k, v in general_tone.items()]

    if len(entries) == 1:
        return entries[0][0]

    entries.sort(key=lambda x: x[1], reverse=True)
    top_label, top_score = entries[0]
    return top_label



def extract_named_entities(raw: dict) -> list[dict]:
    """
    Merge wikidata_entities with xx_ent_wiki_sm spaCy annotations.
    Uses wikidata-confirmed entities as source of truth.
    Enriches with PER/ORG/LOC label from spaCy. Drops MISC and URLs.
    """
    url_pattern = re.compile(r"https?://")
    wikidata_entities = raw.get("wikidata_entities", {})
    spacy_entities = (
        raw.get("spacy_annotations", {})
        .get("xx_ent_wiki_sm", {})
        .get("named_entities", [])
    )

    # Build lookup: raw text → spaCy label
    spacy_label_map: dict[str, str] = {}
    for ent in spacy_entities:
        text = ent.get("text", "")
        label = ent.get("label_", "")
        if label and label != "MISC" and not url_pattern.match(text):
            spacy_label_map[text] = label

    entities = []
    seen_texts = set()

    for text, entry in wikidata_entities.items():
        if url_pattern.match(text):
            continue
        wiki = entry.get("wikidata_entity", {})
        if not wiki:
            continue

        canonical_text = wiki.get("label", text)
        if canonical_text in seen_texts:
            continue
        seen_texts.add(canonical_text)

        spacy_label = spacy_label_map.get(text, "PER")
        if spacy_label == "MISC":
            continue

        entities.append({"text": canonical_text, "label": spacy_label})

    return entities


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

    language = raw.get("language", "")
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
        "subtopics": [],
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