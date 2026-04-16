from app.repositories.classifier_repository import ClassifierRepository
from app.schemas.classification import ClassifierMetadata


class ClassifierLibraryService:
    """CRUD only — never dispatches tasks."""

    def __init__(self, classifier_repo: ClassifierRepository) -> None:
        self._classifier_repo = classifier_repo

    async def save_classifier(self, metadata: ClassifierMetadata) -> None:
        raise NotImplementedError

    async def get_classifier(self, classifier_id: str) -> ClassifierMetadata:
        raise NotImplementedError

    async def list_classifiers(self, user_id: str) -> list[ClassifierMetadata]:
        raise NotImplementedError

    async def delete_classifier(self, classifier_id: str) -> None:
        raise NotImplementedError

    async def export_classifier(self, classifier_id: str) -> bytes:
        raise NotImplementedError
