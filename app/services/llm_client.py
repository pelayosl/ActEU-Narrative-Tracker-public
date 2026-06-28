import json
import logging
import re
import uuid

import httpx

from app.config import settings
from app.schemas.topic import Topic

logger = logging.getLogger(__name__)


class LLMClient:
    """Ollama wrapper for topic reconciliation. Lives in services (not infrastructure)
    because it encapsulates prompt engineering, response parsing, and fallback logic."""

    def reconcile(self, topics: list[Topic]) -> tuple[list[Topic], bool]:
        """Merge similar topics via the university LLM, with a graceful fallback.

        Sends the topics to the LLM with a reconciliation prompt, parses the JSON
        response, and rebuilds the merged topics while preserving every input topic. On
        any failure it logs a warning and returns the unchanged input as a fallback,
        leaving the decision to use or discard it to the caller.

        :param topics: The topics to reconcile.
        :returns: A ``(reconciled_topics, llm_available)`` tuple. When the LLM is
            unavailable the flag is ``False`` and the topics are the unchanged fallback
            list.
        """
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
                    "Authorization": f"Bearer {settings.LLM_API_KEY.get_secret_value()}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": settings.OLLAMA_MODEL,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                },
                timeout=200,
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
            logger.warning(
                "LLM reconciliation failed; returning fallback (llm_available=False)",
                exc_info=True,
            )
            return _fallback(topics), False


def _extract_json(text: str) -> list[dict]:
    """Extract a JSON array from the LLM response, removing markdown code fences.

    :param text: The raw assistant message content.
    :returns: The parsed JSON array.
    :raises json.JSONDecodeError: If the cleaned text is not valid JSON.
    """
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

    :param topic: The topic whose generation-era ids are needed.
    :returns: The topic's ``origin_topic_ids``, or ``[topic_id]`` when it has none.
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

    :param parsed: The LLM-produced groups (each with name, description,
        origin_topic_ids).
    :param valid_ids: The set of legitimate input topic_ids, used to drop
        hallucinated ids.
    :param originals: The original input topics, indexed for id resolution and to
        preserve any the LLM dropped.
    :returns: The reconciled topics, with every input topic represented exactly once.
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
    """Return the original topics unchanged when the LLM call fails entirely.

    :param topics: The input topics to pass through.
    :returns: The same topics, each with its generation-era ``origin_topic_ids``.
    """
    return [
        Topic(
            topic_id=t.topic_id,
            name=t.name,
            description=t.description,
            origin_topic_ids=_generation_ids(t),
        )
        for t in topics
    ]
