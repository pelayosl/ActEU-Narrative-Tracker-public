import asyncio
import json
import logging
import re
import uuid
from collections import defaultdict
from datetime import datetime, timezone

from app.config import settings

import httpx
import numpy as np
from bertopic import BERTopic
from bertopic.representation import BaseRepresentation
from celery import Task
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

from app.config import settings
from app.infrastructure.embedding_cache import EmbeddingCache
from app.tasks.task_context import project_service_context, search_service_context
from app.schemas.project import PendingPipeline
from app.schemas.topic import OTHER_TOPIC_ID, GenerateTopicsResponse, Topic
from app.tasks.celery_app import celery_app


# Embedding model used both to compute vectors and to namespace the embedding cache,
# so a model change can never serve stale vectors.
EMBEDDING_MODEL_NAME = "google/embeddinggemma-300m"

# Minimum number of documents BERTopic/UMAP need to cluster meaningfully.
# Below this, UMAP's k-NN graph collapses to an empty array and fit_transform
# raises "zero-size array to reduction operation maximum".
MIN_DOCUMENTS_FOR_TOPICS = 10


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
        # Set True if any cluster fell back to raw BERTopic labels (LLM unavailable).
        self.llm_failed = False

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
            # Pull the cluster's documents from the `documents` DataFrame that
            # BERTopic passes in (columns: Document / ID / Topic) for getting representative documents.
            rep_docs = documents.loc[documents["Topic"] == topic_id, "Document"].head(4).tolist()
            name, description, llm_ok = _call_ollama(keywords, rep_docs)
            if not llm_ok:
                self.llm_failed = True
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

    if len(text_doc_pairs) < MIN_DOCUMENTS_FOR_TOPICS:
        await _store_pending_pipeline(project_id, job_id, [], {})
        return GenerateTopicsResponse(topics=[]).model_dump()

    texts = [text for text, _ in text_doc_pairs]
    filtered_doc_ids = [doc_id for _, doc_id in text_doc_pairs]

    _update(task, 10, "Computing embeddings")
    embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME, token=settings.HF_TOKEN, trust_remote_code=True)

    # Reuse previously computed vectors; embed only texts not already cached.
    # Keyed by text hash, so the cache survives DB reloads and de-duplicates texts.
    cache = EmbeddingCache(settings.EMBEDDING_CACHE_DIR, EMBEDDING_MODEL_NAME)
    try:
        cached, missing = cache.get_many(texts)
        if missing:
            new_embeddings = embedding_model.encode(missing, show_progress_bar=False)
            cache.store_many(missing, new_embeddings)
            for text, vec in zip(missing, new_embeddings):
                cached[text] = vec
    finally:
        cache.close()
    # Reassemble in input order — BERTopic requires embeddings row-aligned with texts.
    embeddings = np.array([cached[text] for text in texts])

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
    # BERTopic returns a list of topics ordered the same
    # way as input texts, so topic in position 1 corresponds to the
    # input text in position 1.
    # The outlier cluster (-1) is kept too: its documents become the "Other"
    # training set so the classifier can later avoid forcing labels onto docs
    # that match no real topic.
    topic_doc_ids: dict[int, list[str]] = defaultdict(list)
    for idx, bert_topic_id in enumerate(topic_assignments):
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

    # Stash the outlier docs under the reserved "Other" label.
    outlier_doc_ids = topic_doc_ids.get(-1, [])
    if outlier_doc_ids:
        topic_doc_ids_by_topic[OTHER_TOPIC_ID] = outlier_doc_ids

    await _store_pending_pipeline(project_id, job_id, generated_topics, topic_doc_ids_by_topic)
    return GenerateTopicsResponse(
        topics=generated_topics,
        llm_available=not representation.llm_failed,
    ).model_dump()


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


def _call_ollama(keywords: list[str], rep_docs: list[str]) -> tuple[str, str, bool]:
    """Returns (name, description, llm_ok). On any LLM failure, llm_ok is False and
    the labels fall back to the raw BERTopic keywords."""
    keywords_str = ", ".join(keywords[:20])
    docs_str = "\n".join(f"- {doc[:300]}" for doc in rep_docs[:4])

    prompt = (
        "You are a topic labelling assistant. Given keywords and representative documents "
        "from a multilingual political text cluster, produce a concise topic name and a "
        "one-sentence description in English. The documents may be in any language. Respond ONLY in English.\n\n"
        "Don't mention the keywords in your description. Your topic answer will substitute the keywords provided by BERTopic, "
        "and your description must be exclusively centred around providing context to the topic itself.\n\n"
        f"Keywords: {keywords_str}\n\n"
        f"Example documents from this cluster:\n{docs_str}\n\n"
        'Respond ONLY with valid JSON: {"name": "...", "description": "..."}'
    )

    try:
        logger.info("Ollama prompt:\n%s", prompt)
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
        logger.info("Ollama response:\n%s", raw)
        raw = re.sub(r"^```(?:json)?\s*", "", raw)
        raw = re.sub(r"\s*```$", "", raw)
        parsed = json.loads(raw)
        return parsed["name"], parsed["description"], True
    except Exception as e:
        logger.warning("Ollama call failed (%s), using fallback", e)
        name = keywords[0].capitalize() if keywords else "Unknown"
        return name, ", ".join(keywords[:10]), False
