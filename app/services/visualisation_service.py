from app.repositories.document_repository import DocumentRepository
from app.schemas.visualisation import (
    Dashboard,
    LanguageCount,
    PlatformCount,
    TimePoint,
    TopicLanguageBreakdown,
    TopicPlatformBreakdown,
    TopicTimeSeries,
    VisualisationQuery,
)
from app.services.project_service import ProjectService


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

        return Dashboard(
            topic_evolution=topic_evolution,
            topics_by_language=topics_by_language,
            topics_by_platform=topics_by_platform,
            top_actors=[],
            relevant_documents=[],
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
