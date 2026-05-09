import asyncio
import json
import uuid
from collections import defaultdict

import httpx
from bertopic import BERTopic
from bertopic.representation import BaseRepresentation
from redis import Redis
from sentence_transformers import SentenceTransformer

from app.config import settings
from app.infrastructure.task_db import search_service_context
from app.schemas.topic import GenerateTopicsResponse, Topic
from app.tasks.celery_app import celery_app

_TOPIC_MAPPING_KEY_PREFIX = "topic_map:"

class OllamaRepresentation(BaseRepresentation):
    """BERTopic representation model that labels each cluster via the university LLM.
    After fit_transform, access _labels[bert_topic_id] to get (name, description)."""

    def __init__(self) -> None:
        self._labels: dict[int, tuple[str, str]] = {}

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
        updated: dict[int, list[tuple[str, float]]] = {}
        for topic_id, word_scores in topics.items():
            if topic_id == -1: # outlier cluster
                updated[topic_id] = word_scores
                continue
            keywords = [w for w, _ in word_scores[:self.KEYWORD_LIMIT]] # limit num. of keywords to reasonable amount
            rep_docs = topic_model.get_representative_docs(topic_id) or []
            name, description = _call_ollama(keywords, rep_docs)
            self._labels[topic_id] = (name, description)
            # BERTopic uses the first entry as the display label, we add the rest afterwards
            updated[topic_id] = [(name, 1.0)] + [(w, s) for w, s in word_scores[1:]]
        return updated


@celery_app.task(bind=True)
def topic_generation_task(self, doc_ids: list[str]) -> dict:
    """Run BERTopic on the given documents and label each topic via the university LLM."""
    job_id = self.request.id
    return asyncio.run(_run(doc_ids, job_id))


async def _run(doc_ids: list[str], job_id: str) -> dict:
    async with search_service_context() as service:
        docs = await service.get_documents_by_ids(doc_ids)

    # Build parallel (text, doc_id) list — preserves index alignment after filtering
    text_doc_pairs = [
        ((doc.get("plain_text") or "").strip(), str(doc["_id"]))
        for doc in docs
    ]
    text_doc_pairs = [(text, doc_id) for text, doc_id in text_doc_pairs if text]

    if not text_doc_pairs:
        _store_topic_mapping(job_id, {})
        return GenerateTopicsResponse(topics=[]).model_dump()

    if len(text_doc_pairs) < 2:
        # Too few documents to cluster safely.
        _store_topic_mapping(job_id, {})
        return GenerateTopicsResponse(topics=[]).model_dump()

    texts = [text for text, _ in text_doc_pairs]
    filtered_doc_ids = [doc_id for _, doc_id in text_doc_pairs]

    embedding_model = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2")
    embeddings = embedding_model.encode(texts, show_progress_bar=False)

    # Phase 2: Embedding cache hooks go here, future implementation

    representation = OllamaRepresentation()
    min_topic_size = max(2, min(10, len(texts) // 10))
    topic_model = BERTopic(
        embedding_model=embedding_model,
        representation_model=representation,
        calculate_probabilities=False,
        min_topic_size=min_topic_size,
    )
    topic_assignments, _ = topic_model.fit_transform(texts, embeddings)

    # Group filtered_doc_ids by their assigned topic
    topic_doc_ids: dict[int, list[str]] = defaultdict(list)
    for idx, bert_topic_id in enumerate(topic_assignments):
        if bert_topic_id != -1:
            topic_doc_ids[bert_topic_id].append(filtered_doc_ids[idx])

    result = []
    topic_doc_ids_by_topic: dict[str, list[str]] = {}
    for bert_topic_id in topic_model.get_topics():
        if bert_topic_id == -1:
            continue
        name, description = representation._labels.get(bert_topic_id, ("Unknown", ""))
        topic_id = str(uuid.uuid4())
        result.append(
            Topic(
                topic_id=topic_id,
                name=name,
                description=description,
            )
        )
        topic_doc_ids_by_topic[topic_id] = topic_doc_ids.get(bert_topic_id, [])

    _store_topic_mapping(job_id, topic_doc_ids_by_topic)
    return GenerateTopicsResponse(topics=result).model_dump()


def _store_topic_mapping(job_id: str, topic_doc_ids: dict[str, list[str]]) -> None:
    key = f"{_TOPIC_MAPPING_KEY_PREFIX}{job_id}"
    redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        redis.setex(key, settings.TOPIC_MAPPING_TTL_SECONDS, json.dumps(topic_doc_ids))
    finally:
        redis.close()


def _call_ollama(keywords: list[str], rep_docs: list[str]) -> tuple[str, str]:
    keywords_str = ", ".join(keywords[:10])
    docs_str = "\n".join(f"- {doc[:300]}" for doc in rep_docs[:4])

    prompt = (
        "You are a topic labelling assistant. Given keywords and representative documents "
        "from a multilingual political text cluster, produce a concise topic name and a "
        "one-sentence description in English. The documents may be in any language. Respond ONLY in English.\n\n"
        f"Keywords: {keywords_str}\n\n"
        f"Representative documents:\n{docs_str}\n\n"
        'Respond ONLY with valid JSON: {"name": "...", "description": "..."}'
    )

    try:
        response = httpx.post(
            settings.OLLAMA_URL,
            json={"model": settings.OLLAMA_MODEL, "prompt": prompt, "stream": False},
            timeout=120.0,
        )
        parsed = json.loads(response.json()["response"])
        return parsed["name"], parsed["description"]
    except Exception:
        name = keywords[0].capitalize() if keywords else "Unknown"
        return name, ", ".join(keywords[:10])
