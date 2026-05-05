from app.repositories.document_repository import DocumentRepository
from app.schemas.search import DocumentSummary, SearchQuery, SearchResult


class SearchService:
    def __init__(self, document_repo: DocumentRepository) -> None:
        self._document_repo = document_repo

    async def search(self, query: SearchQuery) -> SearchResult:
        docs, total = await self._document_repo.find(query), await self._document_repo.count(query)
        summaries = [self._to_summary(doc) for doc in docs]
        return SearchResult(total_docs=total, retrieved_docs=summaries)

    async def get_documents_by_ids(self, doc_ids: list[str]) -> list[dict]:
        return await self._document_repo.find_by_ids(doc_ids)

    def _to_summary(self, doc: dict) -> DocumentSummary:
        plain_text = (doc.get("plain_text") or "").strip()
        if len(plain_text) > 250:
            excerpt = f"{plain_text[:250].rstrip()}..."
        else:
            excerpt = plain_text

        acteu_topic = doc.get("acteu_topic") or {}
        relevant_topics = [acteu_topic["label"]] if acteu_topic.get("label") else []

        return DocumentSummary(
            doc_id=str(doc["_id"]),
            headline=doc.get("headline") or "",
            excerpt=excerpt,
            platform=doc.get("platform") or "",
            language=doc.get("language") or "",
            date=doc["published_time"],
            relevant_topics=relevant_topics,
        )
