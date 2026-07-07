/**
 * TypeScript mirrors of the backend Pydantic schemas (`app/schemas/*`).
 *
 * These interfaces are the wire contract between the frontend and the FastAPI
 * backend: every value returned by {@link api} (see `lib/api-client.ts`) is typed
 * with one of the shapes declared here. Field names deliberately match the
 * backend JSON (snake_case) so responses can be consumed without remapping.
 *
 * Keep in sync with `app/schemas/*`.
 *
 * @packageDocumentation
 */

/** Source a document was collected from. */
export type Platform = "twitter" | "telegram" | "media";
/** The three fixed core narratives tracked by the platform. */
export type CoreTopic = "immigration" | "climate_change" | "gender_issues";
/** Sentiment polarity assigned to a document. */
export type Sentiment = "positive" | "negative" | "neutral";
/** Application role controlling access (admins can register users). */
export type UserRole = "admin" | "user";

/** A topic (core narrative or a generated/reconciled subtopic). */
export interface Topic {
  topic_id: string;
  name: string;
  description: string;
  /** IDs of the generated topics this one was reconciled/merged from. */
  origin_topic_ids: string[];
}

/** Filter criteria submitted to the search endpoint. */
export interface SearchQuery {
  keywords: string[];
  /** Lower date bound; omitted = no lower bound (full collection). */
  date_from?: string;
  /** Upper date bound; omitted = no upper bound. */
  date_to?: string;
  /** ISO language codes (backend field is `languages`). */
  languages: string[];
  platforms: Platform[];
  topics: string[];
  subtopics: string[];
  /** Minimum classifier confidence, or null/omitted to disable filtering. */
  confidence_threshold?: number | null;
}

/** Condensed document record shown in search result lists. */
export interface DocumentSummary {
  doc_id: string;
  headline: string;
  excerpt: string;
  platform: Platform;
  /** ISO language code (backend field is `language`). */
  language: string;
  /** Published date, or null when the document has no `published_time`. */
  date: string | null;
  relevant_topics: string[];
}

/** A page of search results plus the unpaginated total. */
export interface SearchResult {
  total_docs: number;
  retrieved_docs: DocumentSummary[];
}

/** A selectable topic option in the search form. */
export interface TopicChoice {
  /** Core-topic label (core topics) or `topic_id` (subtopics). */
  value: string;
  label: string;
}

/** Topic facets offered by the search form. */
export interface SearchTopics {
  core_topics: TopicChoice[];
  /** Database subtopics unioned with the project classifier's subtopics. */
  subtopics: TopicChoice[];
}

/** Metadata describing a trained classifier stored on a project. */
export interface ClassifierMetadata {
  classifier_id: string;
  name: string;
  topics: Topic[];
  file_path: string;
  created_at: string;
}

/** A single topic label a classifier assigned to a document. */
export interface ProxyLabel {
  topic_id: string;
  name: string;
  description: string;
  classifier_id: string;
  confidence: number | null;
}

/** All classifier labels attached to one document within a project. */
export interface DocumentProxy {
  doc_id: string;
  labels: ProxyLabel[];
}

/**
 * In-progress topic-modelling pipeline snapshot held on a project until the
 * user finishes (trains a classifier) or discards it.
 */
export interface PendingPipeline {
  generation_job_id: string;
  generated_topics: Topic[];
  reconciled_topics: Topic[];
  /** Reconciled topic id → the generated topic ids merged into it. */
  topic_mapping: Record<string, string[]>;
  created_at: string;
  /** Set once a classifier has been trained from this pipeline. */
  classifier_id: string | null;
}

/** A user's project: its pipeline state, trained classifiers and labels. */
export interface Project {
  project_id: string;
  owner_id: string;
  name: string;
  created_at: string;
  pending_pipeline: PendingPipeline | null;
  classifiers: ClassifierMetadata[];
  document_proxies: DocumentProxy[];
}

/** Outcome of a labelling run: totals and a per-topic document count. */
export interface LabellingResult {
  project_id: string;
  total_labelled: number;
  topic_summary: Record<string, number>;
}

/** Parameters for building a visualisation dashboard. */
export interface VisualisationQuery {
  /** Core label (e.g. `"gender_issues"`) or project subtopic `topic_id` (UUID). */
  topics: string[];
  date_from: string;
  date_to: string;
  languages: string[];
  platforms: Platform[];
  /** Total relevant-documents sample, apportioned across topics. */
  sample_size: number;
}

/** A single point (day + count) in a topic time series. */
export interface TimePoint {
  /** Day in `"YYYY-MM-DD"` format. */
  date: string;
  count: number;
}
/**
 * A topic's document counts over time. The `topic` field is the identifier
 * submitted in the query (core label or subtopic UUID); the UI maps it back to
 * a display name.
 */
export interface TopicTimeSeries {
  topic: string;
  series: TimePoint[];
}

/** Document count for one language. */
export interface LanguageCount {
  language: string;
  count: number;
}
/** A topic's document counts broken down by language. */
export interface TopicLanguageBreakdown {
  topic: string;
  counts: LanguageCount[];
}

/** Document count for one platform. */
export interface PlatformCount {
  platform: string;
  count: number;
}
/** A topic's document counts broken down by platform. */
export interface TopicPlatformBreakdown {
  topic: string;
  counts: PlatformCount[];
}

/** A named entity and its relevance score within a topic. */
export interface EntityScore {
  entity: string;
  score: number;
}
/** The top entities associated with a topic. */
export interface TopicEntities {
  topic: string;
  entities: EntityScore[];
}

/** A representative document surfaced in the dashboard. */
export interface DocumentPreview {
  doc_id: string;
  platform: string;
  language: string;
  date: string;
  topic: string;
  relevance_score: number;
  excerpt: string;
}

/** The full set of series and breakdowns rendered by the visualiser. */
export interface Dashboard {
  topic_evolution: TopicTimeSeries[];
  topics_by_language: TopicLanguageBreakdown[];
  topics_by_platform: TopicPlatformBreakdown[];
  top_entities: TopicEntities[];
  relevant_documents: DocumentPreview[];
}

/** Status of an asynchronous Celery job, polled or streamed by the UI. */
export interface JobStatus {
  job_id: string;
  status: "PENDING" | "STARTED" | "SUCCESS" | "FAILURE";
  /** Completion fraction in the range 0–1. */
  progress: number;
  result: Record<string, unknown>;
}

/** Publicly exposed user fields (never includes the password hash). */
export interface UserPublic {
  user_id: string;
  name: string;
  surname: string;
  username: string;
  role: UserRole;
}

/** Bearer token pair returned by the login endpoint. */
export interface AuthToken {
  access_token: string;
  token_type: string;
}
