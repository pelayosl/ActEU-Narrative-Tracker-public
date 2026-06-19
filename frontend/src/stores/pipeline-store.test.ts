import { beforeEach, describe, expect, it } from "vitest";
import { usePipelineStore } from "./pipeline-store";
import type { Project, Topic } from "@/types/api";

function topic(id: string, overrides: Partial<Topic> = {}): Topic {
  return { topic_id: id, name: `Topic ${id}`, description: `desc ${id}`, origin_topic_ids: [], ...overrides };
}

function makeProject(overrides: Partial<Project> = {}): Project {
  return {
    project_id: "p-1",
    owner_id: "u-1",
    name: "P",
    created_at: "2024-01-01T00:00:00Z",
    pending_pipeline: null,
    classifiers: [],
    document_proxies: [],
    ...overrides,
  };
}

// Reset the singleton store before each test.
beforeEach(() => {
  usePipelineStore.getState().reset();
});

describe("raw topic editing", () => {
  it("updates a generated topic by id", () => {
    const s = usePipelineStore.getState();
    s.setGeneratedTopics([topic("a"), topic("b")]);

    s.updateGeneratedTopic("a", "New", "New desc");

    const updated = usePipelineStore.getState().generatedTopics.find((t) => t.topic_id === "a");
    expect(updated).toMatchObject({ name: "New", description: "New desc" });
  });

  it("deletes a generated topic", () => {
    const s = usePipelineStore.getState();
    s.setGeneratedTopics([topic("a"), topic("b")]);

    s.deleteGeneratedTopic("a");

    expect(usePipelineStore.getState().generatedTopics.map((t) => t.topic_id)).toEqual(["b"]);
  });
});

describe("mergeGeneratedTopics", () => {
  it("merges two topics into one carrying the union of generation ids", () => {
    const s = usePipelineStore.getState();
    s.setGeneratedTopics([topic("a"), topic("b"), topic("c")]);

    s.mergeGeneratedTopics(["a", "b"], "Merged", "Merged desc");

    const topics = usePipelineStore.getState().generatedTopics;
    // c remains, plus a new merged topic
    expect(topics).toHaveLength(2);
    const merged = topics.find((t) => t.name === "Merged")!;
    expect(merged.origin_topic_ids.sort()).toEqual(["a", "b"]);
    expect(topics.some((t) => t.topic_id === "c")).toBe(true);
  });

  it("is a no-op when fewer than two topics are selected", () => {
    const s = usePipelineStore.getState();
    s.setGeneratedTopics([topic("a"), topic("b")]);

    s.mergeGeneratedTopics(["a"], "X", "Y");

    expect(usePipelineStore.getState().generatedTopics).toHaveLength(2);
  });

  it("preserves existing origin ids of an already-merged constituent", () => {
    const s = usePipelineStore.getState();
    s.setGeneratedTopics([topic("m", { origin_topic_ids: ["x", "y"] }), topic("b")]);

    s.mergeGeneratedTopics(["m", "b"], "Merged", "d");

    const merged = usePipelineStore.getState().generatedTopics.find((t) => t.name === "Merged")!;
    expect(merged.origin_topic_ids.sort()).toEqual(["b", "x", "y"]);
  });
});

describe("splitReconciledTopic (RSD.7.3.1 undo-merge)", () => {
  it("restores the original constituents of a reconciled topic", () => {
    const s = usePipelineStore.getState();
    // pre-reconcile generated topics a, b
    s.setGeneratedTopics([topic("a"), topic("b")]);
    s.beginReconciliation("job-1"); // snapshots preReconcileTopics
    // reconciliation produced a single topic fusing a + b
    s.setReconciledTopics([topic("r", { origin_topic_ids: ["a", "b"] })]);

    s.splitReconciledTopic("r");

    const ids = usePipelineStore.getState().reconciledTopics.map((t) => t.topic_id).sort();
    expect(ids).toEqual(["a", "b"]);
  });

  it("is a no-op for an unknown topic id", () => {
    const s = usePipelineStore.getState();
    s.setReconciledTopics([topic("r", { origin_topic_ids: ["a"] })]);

    s.splitReconciledTopic("missing");

    expect(usePipelineStore.getState().reconciledTopics.map((t) => t.topic_id)).toEqual(["r"]);
  });
});

describe("hydrateFromProject", () => {
  it("starts fresh at the search step when there is no pending pipeline", () => {
    usePipelineStore.getState().hydrateFromProject(makeProject());

    const st = usePipelineStore.getState();
    expect(st.currentStep).toBe("search");
    expect(st.hydratedProjectId).toBe("p-1");
  });

  it("resumes at the topics step (generated) when a pipeline is pending without reconciliation", () => {
    usePipelineStore.getState().hydrateFromProject(
      makeProject({
        pending_pipeline: {
          generation_job_id: "g-1",
          generated_topics: [topic("a")],
          reconciled_topics: [],
          topic_mapping: { a: ["d1"] },
          created_at: "2024-01-01T00:00:00Z",
          classifier_id: null,
        },
      }),
    );

    const st = usePipelineStore.getState();
    expect(st.currentStep).toBe("topics");
    expect(st.topicSubStep).toBe("generated");
    expect(st.generatedTopics).toHaveLength(1);
  });

  it("resumes at the label step when the pipeline has a trained classifier", () => {
    usePipelineStore.getState().hydrateFromProject(
      makeProject({
        classifiers: [
          { classifier_id: "c-1", name: "Clf", topics: [], file_path: "/x", created_at: "2024-01-01T00:00:00Z" },
        ],
        pending_pipeline: {
          generation_job_id: "g-1",
          generated_topics: [topic("a")],
          reconciled_topics: [],
          topic_mapping: { a: ["d1", "d2"], b: ["d2", "d3"] },
          created_at: "2024-01-01T00:00:00Z",
          classifier_id: "c-1",
        },
      }),
    );

    const st = usePipelineStore.getState();
    expect(st.currentStep).toBe("label");
    expect(st.trainedClassifier?.classifier_id).toBe("c-1");
    expect(st.resumedDocCount).toBe(3); // unique doc ids across the mapping
  });

  it("is idempotent for the same project (keeps live working state)", () => {
    const project = makeProject();
    const s = usePipelineStore.getState();
    s.hydrateFromProject(project);
    s.setGeneratedTopics([topic("live")]);

    s.hydrateFromProject(project); // second call must not wipe working state

    expect(usePipelineStore.getState().generatedTopics).toHaveLength(1);
  });
});
