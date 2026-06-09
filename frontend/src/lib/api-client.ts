import type {
  AuthToken,
  Dashboard,
  JobStatus,
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

  // Topic modelling (returns job_id, stream via SSE)
  generateTopics: (projectId: string, docIds: string[]) =>
    request<{ job_id: string }>("/topics/generate", {
      method: "POST",
      body: JSON.stringify({ project_id: projectId, doc_ids: docIds }),
    }),
  reconcileTopics: (projectId: string, topics: Topic[]) =>
    request<{ job_id: string }>("/topics/reconcile", {
      method: "POST",
      body: JSON.stringify({ project_id: projectId, topics }),
    }),

  // Classification
  trainClassifier: (projectId: string, name: string, topics: Topic[]) =>
    request<{ job_id: string }>("/classification/train", {
      method: "POST",
      body: JSON.stringify({ project_id: projectId, name, topics }),
    }),
  applyPipelineLabels: (projectId: string, classifierId: string) =>
    request<LabellingResult>("/classification/label/phase1", {
      method: "POST",
      body: JSON.stringify({ project_id: projectId, classifier_id: classifierId }),
    }),
  labelByQuery: (projectId: string, classifierId: string, query: SearchQuery) =>
    request<{ job_id: string }>("/classification/label/phase2", {
      method: "POST",
      body: JSON.stringify({ project_id: projectId, classifier_id: classifierId, query }),
    }),

  // Visualisation
  loadDashboard: (query: VisualisationQuery) =>
    request<Dashboard>("/visualisation/dashboard", {
      method: "POST",
      body: JSON.stringify(query),
    }),

  // Jobs
  getJobStatus: (jobId: string) => request<JobStatus>(`/jobs/${jobId}`),
  streamJob: (jobId: string) => new EventSource(`${BASE_URL}/jobs/${jobId}/stream`),
};
