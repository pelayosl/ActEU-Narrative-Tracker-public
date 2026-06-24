import { http, HttpResponse } from "msw";
import { describe, expect, it } from "vitest";
import { server } from "@/test/msw-server";
import { TEST_ORIGIN } from "@/test/setup";
import { ApiError, api } from "./api-client";

const url = (path: string) => `${TEST_ORIGIN}/api/backend${path}`;

describe("request() behaviour", () => {
  it("sends the bearer token and parses JSON", async () => {
    let seenAuth: string | null = null;
    server.use(
      http.get(url("/projects"), ({ request }) => {
        seenAuth = request.headers.get("authorization");
        return HttpResponse.json([{ project_id: "p-1" }]);
      }),
    );

    const result = await api.listProjects("tok-123");

    expect(seenAuth).toBe("Bearer tok-123");
    expect(result).toEqual([{ project_id: "p-1" }]);
  });

  it("omits the Authorization header when no token is given", async () => {
    let hasAuth = true;
    server.use(
      http.get(url("/search/languages"), ({ request }) => {
        hasAuth = request.headers.has("authorization");
        return HttpResponse.json(["en"]);
      }),
    );

    await api.listLanguages();

    expect(hasAuth).toBe(false);
  });

  it("throws ApiError with the status on a non-2xx response", async () => {
    server.use(
      http.get(url("/projects"), () => new HttpResponse("nope", { status: 403 })),
    );

    await expect(api.listProjects("t")).rejects.toBeInstanceOf(ApiError);
    await expect(api.listProjects("t")).rejects.toMatchObject({ status: 403 });
  });

  it("returns undefined for a 204 response (e.g. DELETE)", async () => {
    server.use(
      http.delete(url("/projects/p-1"), () => new HttpResponse(null, { status: 204 })),
    );

    await expect(api.deleteProject("p-1", "t")).resolves.toBeUndefined();
  });
});

describe("URL / body construction", () => {
  it("passes the project name as a URL-encoded query param", async () => {
    let seenUrl = "";
    server.use(
      http.post(url("/projects"), ({ request }) => {
        seenUrl = new URL(request.url).search;
        return HttpResponse.json({ project_id: "p-1", name: "A B" });
      }),
    );

    await api.createProject("A B", "t");

    expect(seenUrl).toBe("?name=A%20B");
  });

  it("adds project_id to the search URL when supplied", async () => {
    let seenSearch = "";
    server.use(
      http.post(url("/search/"), ({ request }) => {
        seenSearch = new URL(request.url).search;
        return HttpResponse.json({ total_docs: 0, retrieved_docs: [] });
      }),
    );

    await api.search({ keywords: [], languages: [], platforms: [], topics: [], subtopics: [] }, "t", "p-9");

    expect(seenSearch).toBe("?project_id=p-9");
  });

  it("sends the generate-topics body", async () => {
    let body: unknown;
    server.use(
      http.post(url("/topics/generate"), async ({ request }) => {
        body = await request.json();
        return HttpResponse.json({ job_id: "j-1" });
      }),
    );

    const res = await api.generateTopics("p-1", ["d1", "d2"], "t");

    expect(body).toEqual({ project_id: "p-1", doc_ids: ["d1", "d2"] });
    expect(res).toEqual({ job_id: "j-1" });
  });

  it("posts Phase-1 initial labels with project + classifier ids", async () => {
    let body: unknown;
    server.use(
      http.post(url("/classification/label/initial"), async ({ request }) => {
        body = await request.json();
        return HttpResponse.json({ project_id: "p-1", total_labelled: 3, topic_summary: {} });
      }),
    );

    const res = await api.applyPipelineLabels("p-1", "c-1", "t");

    expect(body).toEqual({ project_id: "p-1", classifier_id: "c-1" });
    expect(res.total_labelled).toBe(3);
  });
});

describe("downloadClassifier", () => {
  it("returns the response body as a Blob with the bearer token", async () => {
    let seenAuth: string | null = null;
    server.use(
      http.get(url("/projects/p-1/classifiers/c-1/download"), ({ request }) => {
        seenAuth = request.headers.get("authorization");
        return new HttpResponse("BIN", { status: 200 });
      }),
    );

    const blob = await api.downloadClassifier("p-1", "c-1", "tok");

    expect(seenAuth).toBe("Bearer tok");
    expect(await blob.text()).toBe("BIN");
  });

  it("throws ApiError on a failed download", async () => {
    server.use(
      http.get(url("/projects/p-1/classifiers/c-1/download"), () => new HttpResponse(null, { status: 404 })),
    );

    await expect(api.downloadClassifier("p-1", "c-1", "tok")).rejects.toMatchObject({ status: 404 });
  });
});
