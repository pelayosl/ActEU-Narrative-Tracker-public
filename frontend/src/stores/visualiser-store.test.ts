import { describe, expect, it } from "vitest";
import { buildVisualiserPrefill } from "./visualiser-store";
import type { ClassifierMetadata, SearchQuery } from "@/types/api";

function query(overrides: Partial<SearchQuery> = {}): SearchQuery {
  return {
    keywords: [],
    languages: ["en"],
    platforms: ["twitter"],
    topics: ["immigration"],
    subtopics: [],
    date_from: "2024-01-01T00:00:00Z",
    date_to: "2024-06-01T00:00:00Z",
    ...overrides,
  };
}

describe("buildVisualiserPrefill", () => {
  it("uses the search query topics when no classifier was trained", () => {
    const prefill = buildVisualiserPrefill(query(), null);

    expect(prefill.topics).toEqual(["immigration"]);
    expect(prefill.languages).toEqual(["en"]);
    expect(prefill.platforms).toEqual(["twitter"]);
    expect(prefill.date_from).toBe("2024-01-01T00:00:00Z");
  });

  it("prefers the classifier's subtopics when present", () => {
    const classifier: ClassifierMetadata = {
      classifier_id: "c-1",
      name: "Clf",
      topics: [
        { topic_id: "sub-1", name: "Sub 1", description: "", origin_topic_ids: [] },
        { topic_id: "sub-2", name: "Sub 2", description: "", origin_topic_ids: [] },
      ],
      file_path: "/x",
      created_at: "2024-01-01T00:00:00Z",
    };

    const prefill = buildVisualiserPrefill(query(), classifier);

    expect(prefill.topics).toEqual(["sub-1", "sub-2"]);
  });

  it("falls back to safe defaults when the search query is null", () => {
    const prefill = buildVisualiserPrefill(null, null);

    expect(prefill).toEqual({
      topics: [],
      date_from: undefined,
      date_to: undefined,
      languages: [],
      platforms: [],
    });
  });
});
