"""
Data ingestion main module — ActEU Narrative Tracker
"""

import re
import uuid

# Fixed namespace so a subtopic label always hashes to the same topic_id, on every
# document and every future ingestion batch (uuid5 = content hash of namespace+label).
ACTEU_SUBTOPIC_NS = uuid.UUID("6f1a7b2c-3d4e-5a6b-8c9d-0e1f2a3b4c5d")


def subtopic_id(label: str) -> str:
    """Deterministic, stable topic_id for a db (ACTEU-native) subtopic label."""
    return str(uuid.uuid5(ACTEU_SUBTOPIC_NS, label.strip()))


PRESUMED_ISSUE_MAP = {
    "Migration": "immigration",
    "Climate": "climate_change",
    "Gender": "gender_issues",
}

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
    Extracts core topic from PresumedIssue.
    """
    presumed_issue = annotations.get("PresumedIssue", {})
    if not presumed_issue:
        return None

    core_candidates = [
        (label, conf) for label, conf in presumed_issue.items()
        if label in PRESUMED_ISSUE_MAP
    ]
    if core_candidates:
        best_label, best_confidence = max(core_candidates, key=lambda x: x[1])
        normalised = PRESUMED_ISSUE_MAP[best_label]
        return {"label": normalised, "confidence": best_confidence}

    best_label, best_confidence = max(presumed_issue.items(), key=lambda x: x[1])
    normalised = PRESUMED_ISSUE_MAP.get(best_label)
    if not normalised:
        return None
    return {"label": normalised, "confidence": best_confidence}

def extract_sentiment(annotations: dict) -> str | None:
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
    if len(entries) > 1:
        second_score = entries[1][1]
        if (top_score - second_score) >= 0.20:
            return top_label
        return None
    return top_label

def extract_named_entities(raw: dict) -> list[dict]:
    url_pattern = re.compile(r"https?://")
    wikidata_entities = raw.get("wikidata_entities", {})

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

        entities.append({"text": canonical_text})

    return entities

def extract_acteu_subtopic(annotations: dict) -> list[dict]:
    """
    Extracts all subtopics from FirstSubtopic annotation.
    Skips 'N/A' labels as they are not meaningful.
    Returns a list of subtopic objects, one for each non-N/A label.
    """
    first_subtopic = annotations.get("FirstSubtopic", {})
    if not first_subtopic:
        return []
    
    # Filter out N/A labels
    entries = [(label, conf) for label, conf in first_subtopic.items() if label != "N/A"]
    if not entries:
        return []
    
    return [{
        "topic_id": subtopic_id(label),
        "label": label,
        "confidence": confidence
    } for label, confidence in entries]

