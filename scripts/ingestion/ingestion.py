"""
Data ingestion main module — ActEU Narrative Tracker
"""

import re

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
    If a core topic has confidence above 0.6, it wins over any non-core topic
    """
    presumed_issue = annotations.get("PresumedIssue", {})
    if not presumed_issue:
        return None

    core_candidates = [
        (label, conf) for label, conf in presumed_issue.items()
        if label in PRESUMED_ISSUE_MAP and conf > 0.6
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

