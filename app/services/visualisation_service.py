from app.repositories.document_repository import DocumentRepository
from app.schemas.visualisation import Dashboard, VisualisationQuery
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
        raise NotImplementedError
