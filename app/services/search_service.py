from datetime import datetime

from app.repositories.document_repository import DocumentRepository
from app.schemas.search import DocumentSummary, SearchQuery, SearchResult

EXCERPT_CHARS = 1500


class SearchService:
    """Faceted document search over the core documents collection.

    Turns raw matched documents into presentation summaries (excerpt only, capped at
    ``EXCERPT_CHARS``) and exposes the language facet. Labelling never happens here,
    subtopic proxy doc_ids are resolved by the API gateway and passed in as a union
    source for the underlying query.
    """

    def __init__(self, document_repo: DocumentRepository) -> None:
        """Store the document repository this service reads from.

        :param document_repo: Repository for the core documents collection.
        """
        self._document_repo = document_repo

    async def search(
        self, query: SearchQuery, proxy_doc_ids: list[str] | None = None
    ) -> SearchResult:
        """Run a faceted search and return summaries plus the total match count.

        :param query: The faceted search query.
        :param proxy_doc_ids: Optional project-proxy doc_ids unioned into the query as
            an extra match source.
        :returns: A :class:`SearchResult` with the total count and document summaries.
        """
        docs = await self._document_repo.find(query, proxy_doc_ids)
        total = await self._document_repo.count(query, proxy_doc_ids)
        summaries = [self._to_summary(doc, query) for doc in docs]
        return SearchResult(total_docs=total, retrieved_docs=summaries)

    async def get_documents_by_ids(self, doc_ids: list[str]) -> list[dict]:
        """Fetch full documents by their ids.

        :param doc_ids: The document ids to fetch.
        :returns: The matching raw document dicts.
        """
        return await self._document_repo.find_by_ids(doc_ids)

    async def get_available_languages(self) -> list[str]:
        """Return the distinct languages present in the document collection.

        :returns: The sorted list of language values, backing the search language facet.
        """
        return await self._document_repo.distinct_languages()

    def _matched_subtopic_labels(self, doc: dict, query: SearchQuery) -> list[str]:
        """Pick the document's subtopic labels that the query requested.

        Returns the document-level subtopic labels carried by the doc that the query
        asked for, honouring the confidence threshold when set.

        :param doc: The raw document dict.
        :param query: The search query (its subtopics and confidence threshold are read).
        :returns: The matching subtopic label strings (empty if the query had none).
        """
        if not query.subtopics:
            return []
        requested = set(query.subtopics)
        labels: list[str] = []
        for subtopic in doc.get("subtopics") or []:
            if subtopic.get("topic_id") not in requested:
                continue
            if query.confidence_threshold is not None:
                confidence = subtopic.get("confidence")
                if confidence is None or confidence < query.confidence_threshold:
                    continue
            labels.append(subtopic["label"])
        return labels

    def _to_summary(self, doc: dict, query: SearchQuery) -> DocumentSummary:
        """Build a presentation summary from a raw document.

        Truncates the text to an excerpt of at most ``EXCERPT_CHARS``, collects the
        matched core and subtopic labels into ``relevant_topics``, and coerces a legacy
        non-datetime ``published_time`` to ``None``.

        :param doc: The raw document dict.
        :param query: The search query, used to resolve matched subtopic labels.
        :returns: The :class:`DocumentSummary` for this document.
        """
        plain_text = (doc.get("plain_text") or "").strip()
        if len(plain_text) > EXCERPT_CHARS:
            excerpt = f"{plain_text[:EXCERPT_CHARS].rstrip()}..."
        else:
            excerpt = plain_text

        acteu_topic = doc.get("acteu_topic") or {}
        relevant_topics = [acteu_topic["label"]] if acteu_topic.get("label") else []
        relevant_topics += self._matched_subtopic_labels(doc, query)

        # published_time should be a BSON Date (use loader to convert dates to BSON), but a
        # few records may carry an unparseable legacy string. Ignore and fix manually if detected.
        published_time = doc.get("published_time")
        date = published_time if isinstance(published_time, datetime) else None

        return DocumentSummary(
            doc_id=str(doc["_id"]),
            headline=doc.get("headline") or "",
            excerpt=excerpt,
            platform=doc.get("platform") or "",
            language=doc.get("language") or "",
            date=date,
            relevant_topics=relevant_topics,
        )
