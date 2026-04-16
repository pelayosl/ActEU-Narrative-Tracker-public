from datetime import datetime

from pydantic import BaseModel


class SearchQuery(BaseModel):
    keywords: list[str] = []
    date_from: datetime | None = None
    date_to: datetime | None = None
    countries: list[str] = []
    platforms: list[str] = []
    topics: list[str] = []
    subtopics: list[str] = []


class DocumentSummary(BaseModel):
    doc_id: str
    headline: str
    excerpt: str
    platform: str
    country: str
    date: datetime
    relevant_topics: list[str] = []


class SearchResult(BaseModel):
    total_docs: int
    retrieved_docs: list[DocumentSummary]
