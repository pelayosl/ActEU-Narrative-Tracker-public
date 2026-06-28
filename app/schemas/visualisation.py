from datetime import datetime

from pydantic import BaseModel


class VisualisationQuery(BaseModel):
    """Criteria for a dashboard: topics, date range, language/platform filters and sample size."""

    topics: list[str]
    date_from: datetime
    date_to: datetime
    languages: list[str]
    platforms: list[str]
    sample_size: int = 30


class EntityScore(BaseModel):
    """A single entity with its PageRank centrality score."""

    entity: str
    score: float


class TopicEntities(BaseModel):
    """The top entities for a topic, ranked by PageRank."""

    topic: str
    entities: list[EntityScore]


class TimePoint(BaseModel):
    """A document count for a single day bucket."""

    date: str  # day bucket, formatted "YYYY-MM-DD"
    count: int


class TopicTimeSeries(BaseModel):
    """A topic's daily document counts over the query's date range."""

    topic: str
    series: list[TimePoint]


class LanguageCount(BaseModel):
    """A document count for a single language."""

    language: str
    count: int


class TopicLanguageBreakdown(BaseModel):
    """A topic's document counts broken down by language."""

    topic: str
    counts: list[LanguageCount]


class PlatformCount(BaseModel):
    """A document count for a single platform."""

    platform: str
    count: int


class TopicPlatformBreakdown(BaseModel):
    """A topic's document counts broken down by platform."""

    topic: str
    counts: list[PlatformCount]


class DocumentPreview(BaseModel):
    """A relevance-ranked document shown in the dashboard, with a capped excerpt."""

    doc_id: str
    platform: str
    language: str
    date: datetime
    topic: str
    relevance_score: float
    excerpt: str


class Dashboard(BaseModel):
    """The assembled visualisation dashboard returned for a query."""

    topic_evolution: list[TopicTimeSeries]
    topics_by_language: list[TopicLanguageBreakdown]
    topics_by_platform: list[TopicPlatformBreakdown]
    top_entities: list[TopicEntities]
    relevant_documents: list[DocumentPreview]
