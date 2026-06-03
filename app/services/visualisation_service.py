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

TOP_ENTITIES_LIMIT = 5
RELEVANT_DOCUMENTS_LIMIT = 10
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
        proxy_doc_ids = await self._resolve_proxy_doc_ids(query.topics, project_id)

        topic_evolution = await self._topic_evolution(query, proxy_doc_ids)
        topics_by_language = await self._topics_by_language(query, proxy_doc_ids)
        topics_by_platform = await self._topics_by_platform(query, proxy_doc_ids)
        top_entities_by_topic = await self._top_entities(query, proxy_doc_ids)
        relevant_documents = await self._relevant_documents(query, proxy_doc_ids)

        return Dashboard(
            topic_evolution=topic_evolution,
            topics_by_language=topics_by_language,
            topics_by_platform=topics_by_platform,
            top_entities=top_entities_by_topic,
            relevant_documents=relevant_documents,
        )

    async def _resolve_proxy_doc_ids(
        self, topics: list[str], project_id: str | None
    ) -> dict[str, list[str]]:
        """Resolve, per topic, the project proxy doc_ids that carry it. Returns an empty
        mapping when no project scope is supplied."""
        if not project_id:
            return {}
        return await self._project_service.get_proxy_doc_ids_by_topics(project_id, topics)

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
        self, query: VisualisationQuery, proxy_doc_ids: dict[str, list[str]]
    ) -> list[DocumentPreview]:
        """Single merged list across all query topics: each document's relevance is the
        highest confidence it has for any matched query topic. Deduplicated by document,
        sorted by relevance descending, capped at RELEVANT_DOCUMENTS_LIMIT."""
        best: dict[str, dict] = {}
        for topic in query.topics:
            docs = await self._document_repo.relevant_documents(
                topic,
                query.date_from,
                query.date_to,
                query.languages,
                query.platforms,
                proxy_doc_ids.get(topic),
                limit=RELEVANT_DOCUMENTS_LIMIT,
            )
            for doc in docs:
                doc = {**doc, "topic": topic}
                existing = best.get(doc["doc_id"])
                if existing is None or self._relevance_rank(doc) > self._relevance_rank(existing):
                    best[doc["doc_id"]] = doc

        ranked = sorted(
            best.values(),
            key=lambda d: (self._relevance_rank(d), d["doc_id"]),
            reverse=True,
        )[:RELEVANT_DOCUMENTS_LIMIT]

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
    def _relevance_rank(doc: dict) -> float:
        """Sort key: documents with no confidence (proxy-only matches) rank below any
        confident match."""
        relevance = doc.get("relevance")
        return relevance if relevance is not None else -1.0

    @staticmethod
    def _excerpt(plain_text: str) -> str:
        text = (plain_text or "").strip()
        if len(text) > EXCERPT_MAX_CHARS:
            return f"{text[:EXCERPT_MAX_CHARS].rstrip()}..."
        return text
