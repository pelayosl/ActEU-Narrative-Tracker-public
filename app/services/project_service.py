from app.exceptions import ProjectAccessDenied, ProjectNotFound
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

    async def verify_project_owner(self, project_id: str, user_id: str) -> None:
        """Raises ProjectNotFound or ProjectAccessDenied if the user does not own the project."""
        project = await self._project_repo.find_by_id(project_id)
        if project is None:
            raise ProjectNotFound
        if project.owner_id != user_id:
            raise ProjectAccessDenied

    async def filter_proxies_by_subtopics(
        self, project_id: str, doc_ids: list[str], subtopics: list[str]
    ) -> list[str]:
        """Returns the subset of doc_ids whose project proxies carry at least one of the requested subtopic labels."""
        return await self._project_repo.find_proxy_doc_ids_by_subtopics(project_id, doc_ids, subtopics)

    async def upsert_document_proxies(self, project_id: str, proxies: list[DocumentProxy]) -> None:
        raise NotImplementedError
