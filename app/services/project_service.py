from app.repositories.project_repository import ProjectRepository
from app.repositories.topic_repository import TopicRepository
from app.schemas.classification import ClassifierMetadata, DocumentProxy
from app.schemas.project import Project
from app.schemas.topic import Topic


class ProjectService:
    """CRUD only — never dispatches tasks."""

    def __init__(
        self,
        project_repo: ProjectRepository,
        topic_repo: TopicRepository,
    ) -> None:
        self._project_repo = project_repo
        self._topic_repo = topic_repo

    async def create_project(self, owner_id: str, name: str) -> Project:
        raise NotImplementedError

    async def get_project(self, project_id: str) -> Project:
        raise NotImplementedError

    async def list_projects(self, owner_id: str) -> list[Project]:
        raise NotImplementedError

    async def delete_project(self, project_id: str) -> None:
        raise NotImplementedError

    async def save_classifier(self, project_id: str, classifier: ClassifierMetadata) -> None:
        raise NotImplementedError

    async def get_classifier(self, project_id: str, classifier_id: str) -> ClassifierMetadata:
        raise NotImplementedError

    async def get_available_topics(self, project_id: str) -> list[Topic]:
        """Returns the 3 core topics plus all topics across the project's classifiers."""
        raise NotImplementedError

    async def upsert_document_proxies(self, project_id: str, proxies: list[DocumentProxy]) -> None:
        raise NotImplementedError
