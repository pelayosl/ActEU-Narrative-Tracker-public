from fastapi import APIRouter, Depends

from app.schemas.classification import ClassifierMetadata
from app.services.classifier_library_service import ClassifierLibraryService

router = APIRouter(prefix="/classifiers", tags=["classifiers"])


@router.get("/", response_model=list[ClassifierMetadata])
async def list_classifiers(
    service: ClassifierLibraryService = Depends(),
) -> list[ClassifierMetadata]:
    raise NotImplementedError


@router.get("/{classifier_id}", response_model=ClassifierMetadata)
async def get_classifier(
    classifier_id: str,
    service: ClassifierLibraryService = Depends(),
) -> ClassifierMetadata:
    raise NotImplementedError


@router.delete("/{classifier_id}")
async def delete_classifier(
    classifier_id: str,
    service: ClassifierLibraryService = Depends(),
) -> dict:
    raise NotImplementedError


@router.get("/{classifier_id}/export")
async def export_classifier(
    classifier_id: str,
    service: ClassifierLibraryService = Depends(),
) -> bytes:
    raise NotImplementedError
