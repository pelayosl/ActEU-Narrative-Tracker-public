import json
import re
import uuid

import httpx

from app.config import settings
from app.schemas.topic import Topic


class LLMClient:
    """Ollama wrapper for topic reconciliation. Lives in services (not infrastructure)
    because it encapsulates prompt engineering, response parsing, and fallback logic."""

    def reconcile(self, topics: list[Topic]) -> list[Topic]:
        valid_ids = {t.topic_id for t in topics}
        topics_payload = [
            {"id": t.topic_id, "name": t.name, "description": t.description}
            for t in topics
        ]

        prompt = (
            "You are a topic reconciliation assistant for political text analysis. "
            "Given a list of topics, group similar or overlapping ones and merge each group "
            "into a single unified topic.\n\n"
            "Rules:\n"
            "- Every input topic ID must appear in exactly one output group.\n"
            "- If a topic is distinct enough to stand alone, make it its own group.\n"
            "- Produce a clear English name and one-sentence description for each merged topic.\n\n"
            f"Input topics:\n{json.dumps(topics_payload, ensure_ascii=False, indent=2)}\n\n"
            "Respond ONLY with a valid JSON array:\n"
            '[{"name": "...", "description": "...", "origin_topic_ids": ["id1", "id2"]}, ...]'
        )

        try:
            response = httpx.post(
                settings.OLLAMA_URL,
                json={"model": settings.OLLAMA_MODEL, "prompt": prompt, "stream": False},
                timeout=120.0,
            )
            raw = response.json()["response"]
            parsed = _extract_json(raw)
            return _build_topics(parsed, valid_ids, topics)
        except Exception:
            return _fallback(topics)


def _extract_json(text: str) -> list[dict]:
    """Extract a JSON array from the LLM response, removing markdown code fences."""
    text = text.strip()
    # Strip ```json ... ``` or ``` ... ``` fences if present
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def _build_topics(
    parsed: list[dict],
    valid_ids: set[str],
    originals: list[Topic],
) -> list[Topic]:
    """Validate LLM output and ensure no input topic is lost."""
    covered_ids: set[str] = set()
    result: list[Topic] = []

    for item in parsed:
        # Filter out any IDs the LLM hallucinated
        origin_ids = [oid for oid in item.get("origin_topic_ids", []) if oid in valid_ids]
        if not origin_ids:
            continue
        covered_ids.update(origin_ids)
        result.append(Topic(
            topic_id=str(uuid.uuid4()),
            name=item.get("name", "Unknown"),
            description=item.get("description", ""),
            origin_topic_ids=origin_ids,
        ))

    # Any topic the LLM dropped gets preserved as-is
    for topic in originals:
        if topic.topic_id not in covered_ids:
            result.append(Topic(
                topic_id=str(uuid.uuid4()),
                name=topic.name,
                description=topic.description,
                origin_topic_ids=[topic.topic_id],
            ))

    return result


def _fallback(topics: list[Topic]) -> list[Topic]:
    """Return original topics unchanged if the LLM call fails entirely."""
    return [
        Topic(
            topic_id=str(uuid.uuid4()),
            name=t.name,
            description=t.description,
            origin_topic_ids=[t.topic_id],
        )
        for t in topics
    ]
