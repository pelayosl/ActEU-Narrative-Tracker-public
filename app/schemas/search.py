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
    confidence_threshold: float | None = None


class DocumentSummary(BaseModel):
    doc_id: str
    headline: str
    excerpt: str
    platform: str
    language: str
    date: datetime | None = None
    relevant_topics: list[str] = []


class SearchResult(BaseModel):
    total_docs: int
    retrieved_docs: list[DocumentSummary]


class TopicChoice(BaseModel):
    """A selectable topic in the search form. `value` is what a SearchQuery submits:
    the core_topic label for core topics, the topic_id (UUID) for subtopics."""
    value: str
    label: str


class SearchTopics(BaseModel):
    """Topic facets for the search form, sourced entirely from the database:
    the 3 core ACTEU topics, and the subtopics available for this project
    (document-native db subtopics ∪ the project's classifier subtopics)."""
    core_topics: list[TopicChoice]
    subtopics: list[TopicChoice]
