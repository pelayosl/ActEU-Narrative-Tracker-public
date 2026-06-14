from app.repositories.document_repository import DocumentRepository
from app.schemas.visualisation import (
    Dashboard,
    DocumentPreview,
    EntityScore,
    LanguageCount,
    PlatformCount,
    TimePoint,
    TopicEntities,
    TopicLanguageBreakdown,
    TopicPlatformBreakdown,
    TopicTimeSeries,
    VisualisationQuery,
)
from app.services.pagerank import top_entities
from app.services.project_service import ProjectService

TOP_ENTITIES_LIMIT = 10
EXCERPT_MAX_CHARS = 250


class VisualisationService:
    def __init__(
        self,
        document_repo: DocumentRepository,
        project_service: ProjectService,
    ) -> None:
        self._document_repo = document_repo
        self._project_service = project_service

    async def load_dashboard(
        self, query: VisualisationQuery, project_id: str | None = None
    ) -> Dashboard:
        proxy_confidence = await self._resolve_proxy_confidence(query.topics, project_id)
        # The count/entity blocks only need the matched doc_ids per topic.
        proxy_doc_ids = {topic: list(conf) for topic, conf in proxy_confidence.items()}

        topic_evolution = await self._topic_evolution(query, proxy_doc_ids)
        topics_by_language = await self._topics_by_language(query, proxy_doc_ids)
        topics_by_platform = await self._topics_by_platform(query, proxy_doc_ids)
        top_entities_by_topic = await self._top_entities(query, proxy_doc_ids)
        relevant_documents = await self._relevant_documents(query, proxy_confidence)

        return Dashboard(
            topic_evolution=topic_evolution,
            topics_by_language=topics_by_language,
            topics_by_platform=topics_by_platform,
            top_entities=top_entities_by_topic,
            relevant_documents=relevant_documents,
        )

    async def _resolve_proxy_confidence(
        self, topics: list[str], project_id: str | None
    ) -> dict[str, dict[str, float]]:
        """Resolve, per topic, the project proxy {doc_id: confidence} map. Returns an
        empty mapping when no project scope is supplied."""
        if not project_id:
            return {}
        return await self._project_service.get_proxy_confidence_by_topics(project_id, topics)

    async def _topic_evolution(
        self, query: VisualisationQuery, proxy_doc_ids: dict[str, list[str]]
    ) -> list[TopicTimeSeries]:
        series_list: list[TopicTimeSeries] = []
        for topic in query.topics:
            points = await self._document_repo.topic_presence_over_time(
                topic,
                query.date_from,
                query.date_to,
                query.languages,
                query.platforms,
                proxy_doc_ids.get(topic),
            )
            series_list.append(
                TopicTimeSeries(
                    topic=topic,
                    series=[TimePoint(date=p["date"], count=p["count"]) for p in points],
                )
            )
        return series_list

    async def _topics_by_language(
        self, query: VisualisationQuery, proxy_doc_ids: dict[str, list[str]]
    ) -> list[TopicLanguageBreakdown]:
        breakdowns: list[TopicLanguageBreakdown] = []
        for topic in query.topics:
            counts = await self._document_repo.topic_presence_by_language(
                topic,
                query.date_from,
                query.date_to,
                query.languages,
                query.platforms,
                proxy_doc_ids.get(topic),
            )
            breakdowns.append(
                TopicLanguageBreakdown(
                    topic=topic,
                    counts=[
                        LanguageCount(language=c["language"], count=c["count"])
                        for c in counts
                    ],
                )
            )
        return breakdowns

    async def _topics_by_platform(
        self, query: VisualisationQuery, proxy_doc_ids: dict[str, list[str]]
    ) -> list[TopicPlatformBreakdown]:
        breakdowns: list[TopicPlatformBreakdown] = []
        for topic in query.topics:
            counts = await self._document_repo.topic_presence_by_platform(
                topic,
                query.date_from,
                query.date_to,
                query.languages,
                query.platforms,
                proxy_doc_ids.get(topic),
            )
            breakdowns.append(
                TopicPlatformBreakdown(
                    topic=topic,
                    counts=[
                        PlatformCount(platform=c["platform"], count=c["count"])
                        for c in counts
                    ],
                )
            )
        return breakdowns

    async def _top_entities(
        self, query: VisualisationQuery, proxy_doc_ids: dict[str, list[str]]
    ) -> list[TopicEntities]:
        results: list[TopicEntities] = []
        for topic in query.topics:
            doc_entity_lists = await self._document_repo.entities_for_topic(
                topic,
                query.date_from,
                query.date_to,
                query.languages,
                query.platforms,
                proxy_doc_ids.get(topic),
            )
            ranked = top_entities(doc_entity_lists, limit=TOP_ENTITIES_LIMIT)
            results.append(
                TopicEntities(
                    topic=topic,
                    entities=[
                        EntityScore(entity=name, score=score) for name, score in ranked
                    ],
                )
            )
        return results

    async def _relevant_documents(
        self, query: VisualisationQuery, proxy_confidence: dict[str, dict[str, float]]
    ) -> list[DocumentPreview]:
        """Sample up to `query.sample_size` documents across all query topics. Each
        topic gets a number of slots proportional to its mean classifier confidence
        (minimum 1 each) and shows its own highest-confidence documents. A document
        representative of several query topics may appear once under each of them (so a
        narrow topic that overlaps a broader one still gets its own examples). Slots a
        sparse topic cannot fill are redistributed to the remaining documents of other
        topics, so the sample reaches `sample_size` whenever enough documents exist.
        The result is sorted by relevance descending."""
        if not query.topics:
            return []

        weights: dict[str, float] = {}
        for topic in query.topics:
            mean = await self._document_repo.mean_topic_confidence(
                topic,
                query.date_from,
                query.date_to,
                query.languages,
                query.platforms,
                proxy_confidence.get(topic),
            )
            weights[topic] = mean if mean is not None else 0.0

        slots = self._apportion_slots(weights, query.sample_size)

        # Fetch a deep candidate pool per topic (already sorted by relevance). The
        # final list is at most sample_size docs, so no topic can contribute more.
        pools: dict[str, list[dict]] = {}
        for topic in query.topics:
            docs = await self._document_repo.relevant_documents(
                topic,
                query.date_from,
                query.date_to,
                query.languages,
                query.platforms,
                proxy_confidence.get(topic),
                limit=query.sample_size,
            )
            pools[topic] = [{**doc, "topic": topic} for doc in docs]

        # Pass 1: each topic shows its top documents up to its slot count.
        selected: list[dict] = []
        for topic in query.topics:
            selected.extend(pools[topic][: slots[topic]])
            pools[topic] = pools[topic][slots[topic]:]

        # Pass 2: redistribute slots left unfilled by sparse topics to the best
        # remaining documents of other topics.
        shortfall = query.sample_size - len(selected)
        if shortfall > 0:
            leftover = [doc for topic in query.topics for doc in pools[topic]]
            leftover.sort(
                key=lambda d: (self._relevance_rank(d), d["doc_id"]), reverse=True
            )
            selected.extend(leftover[:shortfall])

        ranked = sorted(
            selected,
            key=lambda d: (self._relevance_rank(d), d["doc_id"]),
            reverse=True,
        )

        return [
            DocumentPreview(
                doc_id=d["doc_id"],
                platform=d["platform"],
                language=d["language"],
                date=d["published_time"],
                topic=d["topic"],
                relevance_score=d["relevance"] if d["relevance"] is not None else 0.0,
                excerpt=self._excerpt(d["plain_text"]),
            )
            for d in ranked
        ]

    @staticmethod
    def _apportion_slots(weights: dict[str, float], sample_size: int) -> dict[str, int]:
        """Split `sample_size` document slots across topics: one guaranteed slot each,
        the remainder distributed proportionally to each topic's weight (mean confidence)
        using the largest-remainder method so the parts sum exactly to `sample_size`.

        Assumes `sample_size >= len(weights)`"""
        topics = list(weights)
        slots = dict.fromkeys(topics, 1)
        remaining = sample_size - len(topics)
        if remaining <= 0:
            return slots

        total_weight = sum(weights.values())
        if total_weight <= 0:
            # No confidence signal anywhere: spread the remainder evenly.
            for i in range(remaining):
                slots[topics[i % len(topics)]] += 1
            return slots

        quotas = {t: remaining * weights[t] / total_weight for t in topics}
        floors = {t: int(q) for t, q in quotas.items()}
        for t in topics:
            slots[t] += floors[t]

        leftover = remaining - sum(floors.values())
        # Hand leftover slots to the largest fractional remainders.
        order = sorted(
            topics, key=lambda t: (quotas[t] - floors[t], weights[t]), reverse=True
        )
        for t in order[:leftover]:
            slots[t] += 1
        return slots

    @staticmethod
    def _relevance_rank(doc: dict) -> float:
        """Sort key: documents with no confidence rank below any
        confident match."""
        relevance = doc.get("relevance")
        return relevance if relevance is not None else -1.0

    @staticmethod
    def _excerpt(plain_text: str) -> str:
        text = (plain_text or "").strip()
        if len(text) > EXCERPT_MAX_CHARS:
            return f"{text[:EXCERPT_MAX_CHARS].rstrip()}..."
        return text
