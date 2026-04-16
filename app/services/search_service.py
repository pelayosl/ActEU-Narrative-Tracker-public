from app.repositories.document_repository import DocumentRepository
from app.schemas.search import SearchQuery, SearchResult


class SearchService:
    def __init__(self, document_repo: DocumentRepository) -> None:
        self._document_repo = document_repo

    async def search(self, query: SearchQuery) -> SearchResult:
        raise NotImplementedError

    async def get_documents_by_ids(self, doc_ids: list[str]) -> list[dict]:
        raise NotImplementedError

    async def update_labels(self, doc_id: str, labels: dict) -> None:
        raise NotImplementedError
