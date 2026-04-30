from datetime import datetime

from pydantic import BaseModel


class SearchQuery(BaseModel):
    keywords: list[str] = []
    date_from: datetime | None = None
    date_to: datetime | None = None
    languages: list[str] = []
    platforms: list[str] = []
    topics: list[str] = []
    subtopics: list[str] = []


class DocumentSummary(BaseModel):
    doc_id: str
    headline: str
    excerpt: str
    platform: str
    language: str
    date: datetime
    relevant_topics: list[str] = []


class SearchResult(BaseModel):
    total_docs: int
    retrieved_docs: list[DocumentSummary]
