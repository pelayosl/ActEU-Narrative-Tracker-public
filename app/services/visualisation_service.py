from app.repositories.document_repository import DocumentRepository
from app.schemas.visualisation import Dashboard, VisualisationQuery


class VisualisationService:
    def __init__(self, document_repo: DocumentRepository) -> None:
        self._document_repo = document_repo

    async def load_dashboard(self, query: VisualisationQuery) -> Dashboard:
        raise NotImplementedError
