// Mirrors backend schemas. Keep in sync with app/schemas/*.

export type Platform = "twitter" | "telegram" | "media";
export type CoreTopic = "immigration" | "climate_change" | "gender_issues";
export type Sentiment = "positive" | "negative" | "neutral";
export type UserRole = "admin" | "user";

export interface Topic {
  topic_id: string;
  name: string;
  description: string;
  origin_topic_ids: string[];
}

export interface SearchQuery {
  keywords: string[];
  date_from: string;
  date_to: string;
  languages: string[]; // backend uses languages; UI labels them as countries
  platforms: Platform[];
  topics: string[];
  subtopics: string[];
}

export interface DocumentSummary {
  doc_id: string;
  headline: string;
  excerpt: string;
  platform: Platform;
  country: string;
  date: string;
  relevant_topics: string[];
}

export interface SearchResult {
  total_docs: number;
  retrieved_docs: DocumentSummary[];
}

export interface ClassifierMetadata {
  classifier_id: string;
  name: string;
  topics: Topic[];
  file_path: string;
  created_at: string;
}

export interface ProxyLabel {
  topic_id: string;
  name: string;
  description: string;
  classifier_id: string;
  confidence: number | null;
}

export interface DocumentProxy {
  doc_id: string;
  labels: ProxyLabel[];
}

export interface PendingPipeline {
  generation_job_id: string;
  generated_topics: Topic[];
  reconciled_topics: Topic[];
  topic_mapping: Record<string, string[]>;
  created_at: string;
}

export interface Project {
  project_id: string;
  owner_id: string;
  name: string;
  created_at: string;
  pending_pipeline: PendingPipeline | null;
  classifiers: ClassifierMetadata[];
  document_proxies: DocumentProxy[];
}

export interface LabellingResult {
  project_id: string;
  total_labelled: number;
  topic_summary: Record<string, number>;
}

export interface VisualisationQuery {
  topics: string[];
  date_from: string;
  date_to: string;
  countries: string[];
  platforms: Platform[];
}

export interface Actor {
  name: string;
  sentiment: Sentiment;
  document_count: number;
}

export interface Dashboard {
  topic_evolution: Array<Record<string, number | string>>;
  topics_by_country: Array<Record<string, number | string>>;
  topics_by_platform: Array<Record<string, number | string>>;
  top_actors: Actor[];
  relevant_documents: DocumentSummary[];
}

export interface JobStatus {
  job_id: string;
  status: "PENDING" | "STARTED" | "SUCCESS" | "FAILURE";
  progress: number;
  result: Record<string, unknown>;
}

export interface UserPublic {
  user_id: string;
  name: string;
  surname: string;
  username: string;
  role: UserRole;
}

export interface AuthToken {
  access_token: string;
  token_type: string;
}
