from datetime import datetime

from pydantic import BaseModel


class VisualisationQuery(BaseModel):
    topics: list[str]
    date_from: datetime
    date_to: datetime
    countries: list[str]
    platforms: list[str]


class Actor(BaseModel):
    name: str
    sentiment: str
    document_count: int


class DocumentPreview(BaseModel):
    doc_id: str
    platform: str
    country: str
    date: datetime
    topic: str
    relevance_score: float
    excerpt: str


class Dashboard(BaseModel):
    topic_evolution: list[dict]
    topics_by_country: list[dict]
    topics_by_platform: list[dict]
    top_actors: list[Actor]
    relevant_documents: list[DocumentPreview]
