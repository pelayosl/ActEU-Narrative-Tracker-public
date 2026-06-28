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
    """Builds the visualisation dashboard from read-only document aggregations.

    For each query topic it assembles presence over time, language and platform
    breakdowns, top entities (via PageRank) and a relevance-ranked document sample.
    Topics resolve against the core documents collection and, when a project scope is
    supplied, against that project's subtopic proxies through :class:`ProjectService`.
    """

    def __init__(
        self,
        document_repo: DocumentRepository,
        project_service: ProjectService,
    ) -> None:
        """Store the document repository and project service this service reads from.

        :param document_repo: Repository for the core documents aggregations.
        :param project_service: Service used to resolve project-scoped subtopics to
            document ids and confidences.
        """
        self._document_repo = document_repo
        self._project_service = project_service

    async def load_dashboard(
        self, query: VisualisationQuery, project_id: str | None = None
    ) -> Dashboard:
        """Assemble the full dashboard for a visualisation query.

        :param query: The visualisation query (topics, date range, languages,
            platforms, sample size).
        :param project_id: Optional project scope, enabling project-subtopic resolution.
        :returns: The assembled :class:`Dashboard`.
        """
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
        """Resolve, per topic, the project proxy ``{doc_id: confidence}`` map.

        :param topics: The query topics to resolve.
        :param project_id: Optional project scope.
        :returns: A ``{topic: {doc_id: confidence}}`` map, empty when no project scope
            is supplied.
        """
        if not project_id:
            return {}
        return await self._project_service.get_proxy_confidence_by_topics(project_id, topics)

    async def _topic_evolution(
        self, query: VisualisationQuery, proxy_doc_ids: dict[str, list[str]]
    ) -> list[TopicTimeSeries]:
        """Build the per-topic daily document-count time series.

        :param query: The visualisation query.
        :param proxy_doc_ids: Per-topic project-proxy doc_ids to union into each match.
        :returns: One :class:`TopicTimeSeries` per query topic.
        """
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
        """Build the per-topic document-count breakdown by language.

        :param query: The visualisation query.
        :param proxy_doc_ids: Per-topic project-proxy doc_ids to union into each match.
        :returns: One :class:`TopicLanguageBreakdown` per query topic.
        """
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
        """Build the per-topic document-count breakdown by platform.

        :param query: The visualisation query.
        :param proxy_doc_ids: Per-topic project-proxy doc_ids to union into each match.
        :returns: One :class:`TopicPlatformBreakdown` per query topic.
        """
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
        """Build the per-topic top entities ranked by PageRank.

        :param query: The visualisation query.
        :param proxy_doc_ids: Per-topic project-proxy doc_ids to union into each match.
        :returns: One :class:`TopicEntities` per query topic, each with up to
            ``TOP_ENTITIES_LIMIT`` entities.
        """
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
        topic gets a number of slots proportional to how many documents it matches
        (minimum 1 each) and shows its own highest-confidence documents. A document
        representative of several query topics may appear once under each of them (so a
        narrow topic that overlaps a broader one still gets its own examples). Slots a
        sparse topic cannot fill are redistributed to the remaining documents of other
        topics, so the sample reaches `sample_size` whenever enough documents exist.
        The result is sorted by relevance descending.

        :param query: The visualisation query (its ``sample_size`` sets the budget).
        :param proxy_confidence: Per-topic ``{doc_id: confidence}`` maps for project
            proxies, used both to match and to rank proxy documents.
        :returns: The sampled :class:`DocumentPreview` list, relevance-ranked.
        """
        if not query.topics:
            return []

        weights: dict[str, float] = {}
        for topic in query.topics:
            count = await self._document_repo.count_topic_documents(
                topic,
                query.date_from,
                query.date_to,
                query.languages,
                query.platforms,
                list(proxy_confidence.get(topic) or {}),
            )
            weights[topic] = float(count)

        slots = self._apportion_slots(weights, query.sample_size)

        # Fetch a candidate pool per topic. The repository returns the top documents
        # of every platform, so the pool is not dominated by whichever platform holds
        # the highest-confidence documents. The pool is then reordered to interleave
        # platforms, so a topic's slots are filled with a varied platform mix. The
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
            pools[topic] = self._diversify_by_platform(
                [{**doc, "topic": topic} for doc in docs]
            )

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
        the remainder distributed proportionally to each topic's weight (document count)
        using the largest-remainder method so the parts sum exactly to `sample_size`.

        Assumes `sample_size >= len(weights)`.

        :param weights: Per-topic weights (document counts) driving the proportional
            split.
        :param sample_size: The total number of slots to distribute.
        :returns: A ``{topic: slot_count}`` map summing to ``sample_size``.
        """
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
    def _diversify_by_platform(docs: list[dict]) -> list[dict]:
        """Reorder a relevance-sorted document list so platforms are interleaved.

        Documents are grouped by platform (each group keeps its relevance order) and
        then drained round-robin, one per platform per round, visiting platforms in
        order of their most relevant document. The head of the list stays
        high-relevance, but no single platform fills the early slots while other
        platforms still have documents to offer. A single-platform list is returned
        unchanged.

        :param docs: A relevance-sorted list of document dicts (with a ``platform`` key).
        :returns: The same documents reordered to interleave platforms.
        """
        if not docs:
            return docs

        groups: dict[str, list[dict]] = {}
        for doc in docs:
            groups.setdefault(doc.get("platform") or "", []).append(doc)
        if len(groups) == 1:
            return docs

        queues = sorted(
            groups.values(),
            key=lambda q: VisualisationService._relevance_rank(q[0]),
            reverse=True,
        )
        result: list[dict] = []
        while any(queues):
            for queue in queues:
                if queue:
                    result.append(queue.pop(0))
        return result

    @staticmethod
    def _relevance_rank(doc: dict) -> float:
        """Compute a sort key where documents with no confidence rank last.

        :param doc: A document dict with an optional ``relevance`` key.
        :returns: The relevance value, or ``-1.0`` when it is absent.
        """
        relevance = doc.get("relevance")
        return relevance if relevance is not None else -1.0

    @staticmethod
    def _excerpt(plain_text: str) -> str:
        """Truncate text to a preview excerpt of at most ``EXCERPT_MAX_CHARS``.

        :param plain_text: The document's full text.
        :returns: The trimmed excerpt, suffixed with ``...`` when truncated.
        """
        text = (plain_text or "").strip()
        if len(text) > EXCERPT_MAX_CHARS:
            return f"{text[:EXCERPT_MAX_CHARS].rstrip()}..."
        return text
