from app.schemas.topic import Topic
from app.services.llm_client import _build_topics, _fallback


def _topic(topic_id: str, origin: list[str] | None = None) -> Topic:
    return Topic(topic_id=topic_id, name=f"name-{topic_id}", description="d", origin_topic_ids=origin or [])


def test_build_topics_keeps_generation_ids_for_raw_topics():
    originals = [_topic("g1"), _topic("g2")]
    parsed = [{"name": "Merged", "description": "x", "origin_topic_ids": ["g1", "g2"]}]

    result = _build_topics(parsed, {"g1", "g2"}, originals)

    assert len(result) == 1
    assert sorted(result[0].origin_topic_ids) == ["g1", "g2"]


def test_build_topics_flattens_manual_merge_to_generation_ids():
    # A manually merged topic 'm' carries its constituents' generation ids.
    merged = _topic("m", origin=["g1", "g2"])
    standalone = _topic("g3")
    originals = [merged, standalone]
    parsed = [{"name": "Reconciled", "description": "x", "origin_topic_ids": ["m", "g3"]}]

    result = _build_topics(parsed, {"m", "g3"}, originals)

    assert len(result) == 1
    # 'm' must be expanded back to g1+g2, never the surface id 'm'
    assert sorted(result[0].origin_topic_ids) == ["g1", "g2", "g3"]
    assert "m" not in result[0].origin_topic_ids


def test_build_topics_preserves_dropped_merged_topic():
    merged = _topic("m", origin=["g1", "g2"])
    originals = [merged]
    parsed: list[dict] = []  # LLM dropped everything

    result = _build_topics(parsed, {"m"}, originals)

    assert len(result) == 1
    assert sorted(result[0].origin_topic_ids) == ["g1", "g2"]


def test_fallback_flattens_merged_topic():
    result = _fallback([_topic("m", origin=["g1", "g2"])])

    assert sorted(result[0].origin_topic_ids) == ["g1", "g2"]
