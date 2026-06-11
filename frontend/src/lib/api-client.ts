import type {
  AuthToken,
  Dashboard,
  LabellingResult,
  Project,
  SearchQuery,
  SearchResult,
  Topic,
  UserPublic,
  VisualisationQuery,
} from "@/types/api";

// Browser calls go through the Next.js proxy (src/app/api/backend/[...path]/route.ts) — no CORS.
const BASE_URL = "/api/backend";

export class ApiError extends Error {
  constructor(public readonly status: number, message: string) {
    super(message);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, init: RequestInit = {}, token?: string): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init.headers ?? {}),
    },
  });
  if (!res.ok) {
    throw new ApiError(res.status, `API error ${res.status}: ${await res.text()}`);
  }
  return res.json() as Promise<T>;
}

export const api = {
  // Auth
  login: (username: string, password: string) =>
    request<AuthToken>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),
  register: (
    form: { name: string; surname: string; username: string; password: string; role: "admin" | "user" },
    token?: string, // admin bearer token — register is admin-only
  ) => request<UserPublic>("/auth/register", { method: "POST", body: JSON.stringify(form) }, token),

  // Projects (all require the user's bearer token)
  listProjects: (token?: string) => request<Project[]>("/projects", {}, token),
  createProject: (
    name: string,
    token?: string, // backend takes `name` as a query parameter, not a body
  ) => request<Project>(`/projects?name=${encodeURIComponent(name)}`, { method: "POST" }, token),
  getProject: (id: string, token?: string) => request<Project>(`/projects/${id}`, {}, token),
  deleteProject: (id: string, token?: string) =>
    request<void>(`/projects/${id}`, { method: "DELETE" }, token),

  // Search facets — languages present in at least one document (dynamic, like topics)
  listLanguages: (token?: string) => request<string[]>("/search/languages", {}, token),

  // Search — project_id is needed only so project-scoped subtopics can be resolved
  search: (query: SearchQuery, token?: string, projectId?: string) =>
    request<SearchResult>(
      `/search/${projectId ? `?project_id=${encodeURIComponent(projectId)}` : ""}`,
      { method: "POST", body: JSON.stringify(query) },
      token,
    ),

  // Topic modelling (returns job_id, polled via getJobStatus)
  generateTopics: (projectId: string, docIds: string[], token?: string) =>
    request<{ job_id: string }>(
      "/topics/generate",
      { method: "POST", body: JSON.stringify({ project_id: projectId, doc_ids: docIds }) },
      token,
    ),
  reconcileTopics: (projectId: string, topics: Topic[], token?: string) =>
    request<{ job_id: string }>(
      "/topics/reconcile",
      { method: "POST", body: JSON.stringify({ project_id: projectId, topics }) },
      token,
    ),

  // Classification
  trainClassifier: (projectId: string, name: string, topics: Topic[], token?: string) =>
    request<{ job_id: string }>(
      "/classification/train",
      { method: "POST", body: JSON.stringify({ project_id: projectId, name, topics }) },
      token,
    ),
  // Phase 1 — synchronous: labels the retrieved docs from the pipeline's topic_mapping.
  applyPipelineLabels: (projectId: string, classifierId: string, token?: string) =>
    request<LabellingResult>(
      "/classification/label/initial",
      { method: "POST", body: JSON.stringify({ project_id: projectId, classifier_id: classifierId }) },
      token,
    ),
  // Phase 2 — async (returns job_id): classifier inference over a new query.
  labelByQuery: (projectId: string, classifierId: string, query: SearchQuery, token?: string) =>
    request<{ job_id: string }>(
      "/classification/label",
      { method: "POST", body: JSON.stringify({ project_id: projectId, classifier_id: classifierId, query }) },
      token,
    ),

  // Visualisation
  loadDashboard: (query: VisualisationQuery) =>
    request<Dashboard>("/visualisation/dashboard", {
      method: "POST",
      body: JSON.stringify(query),
    }),

};
