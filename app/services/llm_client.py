import json
import re
import uuid

import httpx

from app.config import settings
from app.schemas.topic import Topic


class LLMClient:
    """Ollama wrapper for topic reconciliation. Lives in services (not infrastructure)
    because it encapsulates prompt engineering, response parsing, and fallback logic."""

    def reconcile(self, topics: list[Topic]) -> tuple[list[Topic], bool]:
        """Returns (reconciled_topics, llm_available). When the LLM is unavailable the
        flag is False and the second element is the unchanged fallback list — the
        caller decides whether to use or discard it."""
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
                headers={
                    "Authorization": f"Bearer {settings.LLM_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.OLLAMA_MODEL,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                },
                timeout=120,
            )
            data = response.json()
            choices = data.get("choices") or []
            if not choices or not isinstance(choices, list):
                raise ValueError(f"Unexpected LLM response payload: {data}")
            raw = choices[0].get("message", {}).get("content")
            if raw is None:
                raise ValueError(f"Missing assistant content in LLM response: {data}")
            parsed = _extract_json(raw)
            return _build_topics(parsed, valid_ids, topics), True
        except Exception:
            return _fallback(topics), False


def _extract_json(text: str) -> list[dict]:
    """Extract a JSON array from the LLM response, removing markdown code fences."""
    text = text.strip()
    # Strip ```json ... ``` or ``` ... ``` fences if present
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def _generation_ids(topic: Topic) -> list[str]:
    """Generation-era UUIDs a topic resolves to in topic_mapping.

    A manually merged topic carries its constituents' generation ids in
    origin_topic_ids; a raw generated topic uses its own id. Reconciliation must
    propagate these so merged topics keep mapping to their documents at train time.
    """
    return topic.origin_topic_ids if topic.origin_topic_ids else [topic.topic_id]


def _build_topics(
    parsed: list[dict],
    valid_ids: set[str],
    originals: list[Topic],
) -> list[Topic]:
    """Validate LLM output and ensure no input topic is lost.

    The LLM groups by the surface topic_ids it was given, but origin_topic_ids on
    the output must always be generation-era ids (the topic_mapping keys). We
    therefore flatten each surface id back to its generation ids transitively.
    """
    by_id = {t.topic_id: t for t in originals}
    covered_surface_ids: set[str] = set()
    result: list[Topic] = []

    for item in parsed:
        # Filter out any surface IDs the LLM hallucinated
        surface_ids = [oid for oid in item.get("origin_topic_ids", []) if oid in valid_ids]
        if not surface_ids:
            continue
        covered_surface_ids.update(surface_ids)
        origin_ids: list[str] = []
        for sid in surface_ids:
            origin_ids.extend(_generation_ids(by_id[sid]))
        result.append(Topic(
            topic_id=str(uuid.uuid4()),
            name=item.get("name", "Unknown"),
            description=item.get("description", ""),
            origin_topic_ids=origin_ids,
        ))

    # Any topic the LLM dropped gets preserved as-is
    for topic in originals:
        if topic.topic_id not in covered_surface_ids:
            result.append(Topic(
                topic_id=str(uuid.uuid4()),
                name=topic.name,
                description=topic.description,
                origin_topic_ids=_generation_ids(topic),
            ))

    return result


def _fallback(topics: list[Topic]) -> list[Topic]:
    """Return original topics unchanged if the LLM call fails entirely."""
    return [
        Topic(
            topic_id=t.topic_id,
            name=t.name,
            description=t.description,
            origin_topic_ids=_generation_ids(t),
        )
        for t in topics
    ]
