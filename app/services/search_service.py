from app.repositories.document_repository import DocumentRepository
from app.schemas.search import DocumentSummary, SearchQuery, SearchResult

EXCERPT_CHARS = 1500


class SearchService:
    def __init__(self, document_repo: DocumentRepository) -> None:
        self._document_repo = document_repo

    async def search(
        self, query: SearchQuery, proxy_doc_ids: list[str] | None = None
    ) -> SearchResult:
        docs = await self._document_repo.find(query, proxy_doc_ids)
        total = await self._document_repo.count(query, proxy_doc_ids)
        summaries = [self._to_summary(doc, query) for doc in docs]
        return SearchResult(total_docs=total, retrieved_docs=summaries)

    async def get_documents_by_ids(self, doc_ids: list[str]) -> list[dict]:
        return await self._document_repo.find_by_ids(doc_ids)

    async def get_available_languages(self) -> list[str]:
        """Languages present in the document collection"""
        return await self._document_repo.distinct_languages()

    def _matched_subtopic_labels(self, doc: dict, query: SearchQuery) -> list[str]:
        """Document-level (ACTEU-native) subtopic labels carried by the doc that the query
        asked for, honouring the confidence threshold when set."""
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
        plain_text = (doc.get("plain_text") or "").strip()
        if len(plain_text) > EXCERPT_CHARS:
            excerpt = f"{plain_text[:EXCERPT_CHARS].rstrip()}..."
        else:
            excerpt = plain_text

        acteu_topic = doc.get("acteu_topic") or {}
        relevant_topics = [acteu_topic["label"]] if acteu_topic.get("label") else []
        relevant_topics += self._matched_subtopic_labels(doc, query)

        return DocumentSummary(
            doc_id=str(doc["_id"]),
            headline=doc.get("headline") or "",
            excerpt=excerpt,
            platform=doc.get("platform") or "",
            language=doc.get("language") or "",
            date=doc.get("published_time"),
            relevant_topics=relevant_topics,
        )
