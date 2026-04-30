from datetime import datetime

from pydantic import BaseModel

from app.schemas.classification import ClassifierMetadata, DocumentProxy


class Project(BaseModel):
    project_id: str
    owner_id: str
    name: str
    created_at: datetime
    classifiers: list[ClassifierMetadata] = []
    document_proxies: list[DocumentProxy] = []
