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

// Browser calls go through the Next.js proxy (see next.config.mjs rewrite) — no CORS.
const BASE_URL = "/api/backend";

async function request<T>(path: string, init: RequestInit = {}, token?: string): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init.headers ?? {}),
    },
  });
  if (!res.ok) throw new Error(`API error ${res.status}: ${await res.text()}`);
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

  // Projects
  listProjects: () => request<Project[]>("/projects"),
  createProject: (name: string) =>
    request<Project>("/projects", { method: "POST", body: JSON.stringify({ name }) }),
  getProject: (id: string) => request<Project>(`/projects/${id}`),
  deleteProject: (id: string) => request<void>(`/projects/${id}`, { method: "DELETE" }),

  // Search
  search: (query: SearchQuery) =>
    request<SearchResult>("/search", { method: "POST", body: JSON.stringify(query) }),

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
