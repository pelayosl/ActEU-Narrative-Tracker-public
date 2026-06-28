from datetime import datetime

from pydantic import BaseModel


class SearchQuery(BaseModel):
    """Faceted search criteria over the documents collection.

    ``confidence_threshold`` is a single minimum confidence applied uniformly to topic
    and subtopic matches.
    """

    keywords: list[str] = []
    date_from: datetime | None = None
    date_to: datetime | None = None
    languages: list[str] = []
    platforms: list[str] = []
    topics: list[str] = []
    subtopics: list[str] = []
    confidence_threshold: float | None = None


class DocumentSummary(BaseModel):
    """Presentation view of a matched document, carrying an excerpt rather than full text."""

    doc_id: str
    headline: str
    excerpt: str
    platform: str
    language: str
    date: datetime | None = None
    relevant_topics: list[str] = []


class SearchResult(BaseModel):
    """A page of search results: the total match count and the returned summaries."""

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
