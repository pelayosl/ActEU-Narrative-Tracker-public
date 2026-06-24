"""NLP-heavy tests for TopicGenerationTask.

Marked `slow`: runs real BERTopic + sentence-transformers embeddings
(requirements-nlp.txt) and downloads the embedding model on first run. The
university LLM call (`_call_ollama`) is mocked so no network LLM is needed;
Mongo access is mocked. Excluded from CI; run locally.

BERTopic/HDBSCAN clustering over a small corpus is non-deterministic, so the
assertions check structural invariants (pipeline persisted, topic_mapping
consistent with generated topics) rather than exact topic counts.
"""
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, Mock, patch

import pytest

pytest.importorskip("bertopic")
pytest.importorskip("sentence_transformers")

from app.schemas.project import PendingPipeline
from app.schemas.topic import OTHER_TOPIC_ID
from app.tasks import topic_generation_task as task_mod

pytestmark = pytest.mark.slow


# Two clearly separated themes, with lexical variety so BERTopic forms clusters.
IMMIGRATION = [
    "the government announced new border control and immigration policy",
    "migrants crossing the border face asylum application delays",
    "refugees seek asylum after fleeing across the southern border",
    "the immigration debate centres on visas and border security",
    "asylum seekers wait months for residency and migration permits",
    "border patrol intercepted migrants attempting an illegal crossing",
    "the new migration law tightens rules for refugees and asylum",
    "immigration officials processed thousands of visa applications",
    "deportation of undocumented migrants sparked a border protest",
    "the asylum system struggles with the surge of migrants at the border",
    "lawmakers debated immigration reform and border wall funding",
    "refugee resettlement programs expanded for migrants seeking asylum",
]
CLIMATE = [
    "rising global temperatures accelerate climate change worldwide",
    "carbon emissions drive global warming and extreme weather",
    "renewable energy reduces greenhouse gas emissions and pollution",
    "the climate summit pledged to cut carbon emissions sharply",
    "melting glaciers and rising sea levels threaten coastal cities",
    "solar and wind power expand to fight climate change",
    "scientists warn of irreversible warming from fossil fuel emissions",
    "the heatwave and drought are linked to global climate change",
    "governments invest in clean energy to lower carbon footprints",
    "deforestation worsens climate change by releasing stored carbon",
    "the climate crisis demands urgent cuts to greenhouse gases",
    "extreme weather events intensify as the planet keeps warming",
]


def actx(value):
    @asynccontextmanager
    async def _cm(*args, **kwargs):
        yield value
    return _cm


def raw_docs(texts) -> list[dict]:
    return [{"_id": f"doc-{i}", "plain_text": t} for i, t in enumerate(texts)]


async def run_generation(texts, *, llm_label=("Topic", "A description", True)):
    """Drive _run with mocked services and a mocked LLM, real embeddings/clustering."""
    task = Mock()  # provides update_state(); _run does not read other attrs
    project_service = AsyncMock()
    search_service = AsyncMock()
    search_service.get_documents_by_ids.return_value = raw_docs(texts)

    with patch.object(task_mod, "project_service_context", actx(project_service)), \
         patch.object(task_mod, "search_service_context", actx(search_service)), \
         patch.object(task_mod, "_call_ollama", return_value=llm_label):
        result = await task_mod._run(task, "proj-1", [d["_id"] for d in raw_docs(texts)], "job-1")
    return result, project_service


def stored_pipeline(project_service) -> PendingPipeline:
    project_service.set_pending_pipeline.assert_awaited_once()
    return project_service.set_pending_pipeline.call_args.args[1]


# ---------------------------------------------------------------------------
# Below-threshold short-circuit (cheap — no embeddings computed)
# ---------------------------------------------------------------------------

class TestBelowThreshold:
    async def test_too_few_docs_returns_empty_and_stores_empty_pipeline(self):
        texts = IMMIGRATION[: task_mod.MIN_DOCUMENTS_FOR_TOPICS - 1]

        result, project_service = await run_generation(texts)

        assert result["topics"] == []
        pipeline = stored_pipeline(project_service)
        assert pipeline.generated_topics == []
        assert pipeline.topic_mapping == {}

    async def test_blank_docs_are_dropped_below_threshold(self):
        texts = ["   ", "", "  "]
        result, project_service = await run_generation(texts)

        assert result["topics"] == []
        project_service.set_pending_pipeline.assert_awaited_once()


# ---------------------------------------------------------------------------
# Full BERTopic run (heavy)
# ---------------------------------------------------------------------------

class TestGeneration:
    async def test_response_shape_and_pipeline_persisted(self):
        texts = IMMIGRATION + CLIMATE

        result, project_service = await run_generation(texts)

        assert isinstance(result["topics"], list)
        assert "llm_available" in result

        pipeline = stored_pipeline(project_service)
        # Every generated topic must have an entry in the topic_mapping.
        for topic in pipeline.generated_topics:
            assert topic.topic_id in pipeline.topic_mapping
        # The persisted generated_topics match the returned topics.
        assert {t.topic_id for t in pipeline.generated_topics} == {
            t["topic_id"] for t in result["topics"]
        }

    async def test_topic_mapping_only_references_input_docs(self):
        texts = IMMIGRATION + CLIMATE
        valid_ids = {f"doc-{i}" for i in range(len(texts))}

        _result, project_service = await run_generation(texts)
        pipeline = stored_pipeline(project_service)

        for doc_ids in pipeline.topic_mapping.values():
            assert set(doc_ids) <= valid_ids
        # Reserved outlier key, if present, is never a generated topic.
        generated_ids = {t.topic_id for t in pipeline.generated_topics}
        assert OTHER_TOPIC_ID not in generated_ids

    async def test_llm_unavailable_propagates_when_topics_form(self):
        texts = IMMIGRATION + CLIMATE

        result, _ = await run_generation(
            texts, llm_label=("keyword", "keyword", False)
        )

        if not result["topics"]:
            pytest.skip("BERTopic produced no topics for this run; nothing to label")
        assert result["llm_available"] is False
