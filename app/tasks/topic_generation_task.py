import asyncio
import json
import logging
import re
import uuid
from collections import defaultdict
from datetime import datetime, timezone

import httpx
from bertopic import BERTopic
from bertopic.representation import BaseRepresentation
from celery import Task
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

from app.config import settings
from app.infrastructure.task_db import project_service_context, search_service_context
from app.schemas.project import PendingPipeline
from app.schemas.topic import GenerateTopicsResponse, Topic
from app.tasks.celery_app import celery_app


def _update(task: Task, progress: int, step: str) -> None:
    task.update_state(state="PROGRESS", meta={"progress": progress, "step": step})


class OllamaRepresentation(BaseRepresentation):
    """BERTopic representation model that labels each cluster via the university LLM.
    After fit_transform, access _labels[bert_topic_id] to get (name, description)."""

    def __init__(self, task: Task, topic_count_ref: list) -> None:
        self._labels: dict[int, tuple[str, str]] = {}
        self._task = task
        # topic_count_ref is a single-element list so we can mutate it from extract_topics
        # after clustering is done and the number of topics is known
        self._topic_count_ref = topic_count_ref
        self._labelled = 0

    KEYWORD_LIMIT = 10

    '''
    * Built-in BERTopic representation model hook. Without it, BERTopic uses the raw
      c-TF-IDF keywords at the topic label.
    * This function uses Ollama with keywords + representative docs to produce
      human-readable names and descriptions for each cluster
    * This runs during fit_transform, it is not a post-processing operation
    '''
    def extract_topics(
        self,
        topic_model,
        documents,  # pd.DataFrame with Document / Topic / ID columns
        c_tf_idf,
        topics: dict[int, list[tuple[str, float]]], # 0: [("migration", 0.85), ("border", 0.72), ("asylum", 0.61), ...], ...
    ) -> dict[int, list[tuple[str, float]]]:
        real_topics = [tid for tid in topics if tid != -1]
        self._topic_count_ref[0] = len(real_topics)

        updated: dict[int, list[tuple[str, float]]] = {}
        for topic_id, word_scores in topics.items():
            if topic_id == -1: # outlier cluster
                updated[topic_id] = word_scores
                continue
            keywords = [w for w, _ in word_scores[:self.KEYWORD_LIMIT]]
            rep_docs = topic_model.get_representative_docs(topic_id) or []
            name, description = _call_ollama(keywords, rep_docs)
            self._labels[topic_id] = (name, description)
            # BERTopic uses the first entry as the display label, we add the rest afterwards
            updated[topic_id] = [(name, 1.0)] + [(w, s) for w, s in word_scores[1:]]

            self._labelled += 1
            total = self._topic_count_ref[0] or 1
            # LLM labelling spans 65–95%
            progress = 65 + int((self._labelled / total) * 30)
            _update(self._task, progress, f"Labelling topic {self._labelled}/{total}")

        return updated


@celery_app.task(bind=True)
def topic_generation_task(self, project_id: str, doc_ids: list[str]) -> dict:
    """Run BERTopic on the given documents and label each topic via the university LLM."""
    job_id = self.request.id
    return asyncio.run(_run(self, project_id, doc_ids, job_id))


async def _run(task: Task, project_id: str, doc_ids: list[str], job_id: str) -> dict:
    _update(task, 5, "Fetching documents")
    async with search_service_context() as service:
        docs = await service.get_documents_by_ids(doc_ids)

    # Build parallel (text, doc_id) list — preserves index alignment after filtering
    text_doc_pairs = [
        ((doc.get("plain_text") or "").strip(), str(doc["_id"]))
        for doc in docs
    ]
    text_doc_pairs = [(text, doc_id) for text, doc_id in text_doc_pairs if text]

    if len(text_doc_pairs) < 2:
        await _store_pending_pipeline(project_id, job_id, [], {})
        return GenerateTopicsResponse(topics=[]).model_dump()

    texts = [text for text, _ in text_doc_pairs]
    filtered_doc_ids = [doc_id for _, doc_id in text_doc_pairs]

    _update(task, 10, "Computing embeddings")
    embedding_model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    embeddings = embedding_model.encode(texts, show_progress_bar=False)

    # Phase 2: Embedding cache hooks go here, future implementation

    _update(task, 40, "Clustering documents")
    topic_count_ref = [0]
    representation = OllamaRepresentation(task, topic_count_ref)
    min_topic_size = max(2, min(10, len(texts) // 10))
    topic_model = BERTopic(
        embedding_model=embedding_model,
        representation_model=representation,
        calculate_probabilities=False,
        min_topic_size=min_topic_size,
    )
    # fit_transform runs UMAP + HDBSCAN then calls representation.extract_topics()
    # which emits PROGRESS updates per topic during LLM labelling
    topic_assignments, _ = topic_model.fit_transform(texts, embeddings)

    _update(task, 97, "Storing results")

    # Group filtered_doc_ids by their assigned topic
    topic_doc_ids: dict[int, list[str]] = defaultdict(list)
    for idx, bert_topic_id in enumerate(topic_assignments):
        if bert_topic_id != -1:
            topic_doc_ids[bert_topic_id].append(filtered_doc_ids[idx])

    generated_topics: list[Topic] = []
    topic_doc_ids_by_topic: dict[str, list[str]] = {}
    for bert_topic_id in topic_model.get_topics():
        if bert_topic_id == -1:
            continue
        name, description = representation._labels.get(bert_topic_id, ("Unknown", ""))
        topic_id = str(uuid.uuid4())
        generated_topics.append(
            Topic(
                topic_id=topic_id,
                name=name,
                description=description,
            )
        )
        topic_doc_ids_by_topic[topic_id] = topic_doc_ids.get(bert_topic_id, [])

    await _store_pending_pipeline(project_id, job_id, generated_topics, topic_doc_ids_by_topic)
    return GenerateTopicsResponse(topics=generated_topics).model_dump()


async def _store_pending_pipeline(
    project_id: str,
    job_id: str,
    generated_topics: list[Topic],
    topic_mapping: dict[str, list[str]],
) -> None:
    pipeline = PendingPipeline(
        generation_job_id=job_id,
        generated_topics=generated_topics,
        reconciled_topics=[],
        topic_mapping=topic_mapping,
        created_at=datetime.now(timezone.utc),
    )
    async with project_service_context() as project_service:
        await project_service.set_pending_pipeline(project_id, pipeline)


def _call_ollama(keywords: list[str], rep_docs: list[str]) -> tuple[str, str]:
    keywords_str = ", ".join(keywords[:10])
    docs_str = "\n".join(f"- {doc[:300]}" for doc in rep_docs[:4])

    prompt = (
        "You are a topic labelling assistant. Given keywords and representative documents "
        "from a multilingual political text cluster, produce a concise topic name and a "
        "one-sentence description in English. The documents may be in any language. Respond ONLY in English.\n\n"
        "Don't mention the keywords in your description. Your topic answer will substitute the keywords provided by BERTopic, "
        "and your description must be exclusively centred around providing context to the topic itself.\n\n"
        f"Keywords: {keywords_str}\n\n"
        f"Representative documents:\n{docs_str}\n\n"
        'Respond ONLY with valid JSON: {"name": "...", "description": "..."}'
    )

    try:
        logger.info("Ollama prompt:\n%s", prompt)
        response = httpx.post(
            settings.OLLAMA_URL,
            json={"model": settings.OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=120.0,
        )
        raw = response.json()["response"]
        logger.info("Ollama response:\n%s", raw)
        raw = raw.strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        parsed = json.loads(raw)
        return parsed["name"], parsed["description"]
    except Exception as e:
        logger.warning("Ollama call failed (%s), using fallback", e)
        name = keywords[0].capitalize() if keywords else "Unknown"
        return name, ", ".join(keywords[:10])
