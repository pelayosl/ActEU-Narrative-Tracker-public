/**
 * Central store driving the multi-step topic-modelling pipeline.
 *
 * Holds every piece of pipeline state — the current step, the search query and
 * results, the generated and reconciled topic lists, running job ids, the
 * trained classifier and labelling results — plus the actions that mutate them,
 * including the frontend-only topic editing (rename, delete, merge, split). It
 * can be rehydrated from a project's `pending_pipeline` so an interrupted
 * pipeline resumes at the right step.
 *
 * @packageDocumentation
 */
import { create } from "zustand";
import type {
  ClassifierMetadata,
  LabellingResult,
  Project,
  SearchQuery,
  SearchResult,
  Topic,
} from "@/types/api";

/** The three top-level pipeline steps. */
export type PipelineStep = "search" | "topics" | "label";
/** Sub-states within the "topics" step (generation then reconciliation). */
export type TopicSubStep = "generating" | "generated" | "reconciling" | "reconciled";

/**
 * The generation-era ids a topic resolves to in the backend `topic_mapping`.
 *
 * A merged topic carries its constituents' ids in `origin_topic_ids`; a raw one
 * uses its own id. Kept in sync with the backend
 * (`llm_client._generation_ids` / training task).
 *
 * @param topic - The topic to resolve.
 * @returns The generation ids this topic maps to.
 */
function generationIds(topic: Topic): string[] {
  return topic.origin_topic_ids.length > 0 ? topic.origin_topic_ids : [topic.topic_id];
}

/** Full state and action surface of the pipeline store. */
interface PipelineState {
  currentStep: PipelineStep;
  topicSubStep: TopicSubStep | null;

  searchQuery: SearchQuery | null;
  searchResult: SearchResult | null;
  generatedTopics: Topic[];
  reconciledTopics: Topic[];
  // Snapshot of the (possibly edited/merged) topic list sent to reconciliation,
  // used to restore the original constituents when a reconciled topic is split.
  preReconcileTopics: Topic[];
  generationJobId: string | null;
  reconciliationJobId: string | null;
  trainedClassifier: ClassifierMetadata | null;
  // Labelling results, kept here so they survive re-renders and a phase-1 result
  // can't be re-triggered after the backend clears the pending pipeline.
  phase1Result: LabellingResult | null;
  phase2Result: LabellingResult | null;
  // Resumption: which project the store was last hydrated for, and the document
  // count derived from a resumed topic_mapping (searchResult is not persisted).
  hydratedProjectId: string | null;
  resumedDocCount: number | null;

  setStep: (step: PipelineStep) => void;
  setTopicSubStep: (s: TopicSubStep | null) => void;
  setSearchQuery: (q: SearchQuery) => void;
  setSearchResult: (r: SearchResult) => void;
  setGeneratedTopics: (topics: Topic[]) => void;
  setReconciledTopics: (topics: Topic[]) => void;
  setGenerationJobId: (id: string | null) => void;
  setReconciliationJobId: (id: string | null) => void;
  setTrainedClassifier: (c: ClassifierMetadata) => void;
  setPhase1Result: (r: LabellingResult) => void;
  setPhase2Result: (r: LabellingResult) => void;

  // 2b — raw topic editing (frontend only, never written back to the backend
  // until reconciliation or training is triggered with the current list).
  updateGeneratedTopic: (topicId: string, name: string, description: string) => void;
  deleteGeneratedTopic: (topicId: string) => void;
  mergeGeneratedTopics: (topicIds: string[], name: string, description: string) => void;

  // 2c — reconciled topic editing
  updateReconciledTopic: (topicId: string, name: string, description: string) => void;
  // Deleting a reconciled topic splits it back into its original constituents.
  splitReconciledTopic: (topicId: string) => void;

  beginReconciliation: (jobId: string) => void;
  cancelReconciliation: () => void;
  // Restore pipeline state from a project's pending_pipeline when entering the
  // pipeline. Idempotent per project (guarded by hydratedProjectId).
  hydrateFromProject: (project: Project) => void;
  reset: () => void;
}

const initial = {
  currentStep: "search" as PipelineStep,
  topicSubStep: null,
  searchQuery: null,
  searchResult: null,
  generatedTopics: [],
  reconciledTopics: [],
  preReconcileTopics: [],
  generationJobId: null,
  reconciliationJobId: null,
  trainedClassifier: null,
  phase1Result: null,
  phase2Result: null,
  hydratedProjectId: null,
  resumedDocCount: null,
};

/**
 * Count unique document ids across a `topic_mapping`.
 *
 * Used to show the document count when a pipeline is resumed and the original
 * `searchResult` is no longer in memory.
 *
 * @param topicMapping - Reconciled topic id → document ids.
 * @returns The number of distinct document ids across all topics.
 */
function countMappedDocs(topicMapping: Record<string, string[]>): number {
  const ids = new Set<string>();
  for (const docIds of Object.values(topicMapping)) {
    for (const id of docIds) ids.add(id);
  }
  return ids.size;
}

/** Zustand hook exposing the full pipeline state and its actions. */
export const usePipelineStore = create<PipelineState>((set) => ({
  ...initial,
  setStep: (step) => set({ currentStep: step }),
  setTopicSubStep: (s) => set({ topicSubStep: s }),
  setSearchQuery: (q) => set({ searchQuery: q }),
  setSearchResult: (r) => set({ searchResult: r }),
  setGeneratedTopics: (topics) => set({ generatedTopics: topics }),
  setReconciledTopics: (topics) => set({ reconciledTopics: topics }),
  setGenerationJobId: (id) => set({ generationJobId: id }),
  setReconciliationJobId: (id) => set({ reconciliationJobId: id }),
  setTrainedClassifier: (c) => set({ trainedClassifier: c }),
  setPhase1Result: (r) => set({ phase1Result: r }),
  setPhase2Result: (r) => set({ phase2Result: r }),

  updateGeneratedTopic: (topicId, name, description) =>
    set((s) => ({
      generatedTopics: s.generatedTopics.map((t) =>
        t.topic_id === topicId ? { ...t, name, description } : t,
      ),
    })),

  deleteGeneratedTopic: (topicId) =>
    set((s) => ({
      generatedTopics: s.generatedTopics.filter((t) => t.topic_id !== topicId),
    })),

  mergeGeneratedTopics: (topicIds, name, description) =>
    set((s) => {
      const selected = s.generatedTopics.filter((t) => topicIds.includes(t.topic_id));
      if (selected.length < 2) return {};
      // Union the constituents' generation ids so the merged topic still maps to
      // their documents at training/labelling time.
      const origin = [...new Set(selected.flatMap(generationIds))];
      const merged: Topic = {
        topic_id: crypto.randomUUID(),
        name,
        description,
        origin_topic_ids: origin,
      };
      const rest = s.generatedTopics.filter((t) => !topicIds.includes(t.topic_id));
      return { generatedTopics: [...rest, merged] };
    }),

  updateReconciledTopic: (topicId, name, description) =>
    set((s) => ({
      reconciledTopics: s.reconciledTopics.map((t) =>
        t.topic_id === topicId ? { ...t, name, description } : t,
      ),
    })),

  splitReconciledTopic: (topicId) =>
    set((s) => {
      const target = s.reconciledTopics.find((t) => t.topic_id === topicId);
      if (!target) return {};
      const originSet = new Set(target.origin_topic_ids);
      // Restore the pre-reconciliation topics whose generation ids fed this topic.
      const constituents = s.preReconcileTopics.filter((t) =>
        generationIds(t).some((id) => originSet.has(id)),
      );
      const remaining = s.reconciledTopics.filter((t) => t.topic_id !== topicId);
      const existingIds = new Set(remaining.map((t) => t.topic_id));
      const restored = constituents.filter((t) => !existingIds.has(t.topic_id));
      return { reconciledTopics: [...remaining, ...restored] };
    }),

  beginReconciliation: (jobId) =>
    set((s) => ({
      preReconcileTopics: s.generatedTopics,
      reconciliationJobId: jobId,
      topicSubStep: "reconciling",
    })),

  cancelReconciliation: () =>
    set({ reconciledTopics: [], reconciliationJobId: null, topicSubStep: "generated" }),

  hydrateFromProject: (project) =>
    set((s) => {
      // Already hydrated for this project — keep any live working state.
      if (s.hydratedProjectId === project.project_id) return {};

      const pp = project.pending_pipeline;
      // No pending pipeline → fresh start at the search step.
      if (!pp) {
        return { ...initial, hydratedProjectId: project.project_id };
      }

      const base = {
        ...initial,
        hydratedProjectId: project.project_id,
        generatedTopics: pp.generated_topics,
        reconciledTopics: pp.reconciled_topics,
        preReconcileTopics: pp.generated_topics,
        generationJobId: pp.generation_job_id || null,
        // The original searchResult is not persisted, so derive the document
        // count from the topic_mapping for every resumed path — it's needed once
        // the user reaches the labelling step (whether already there or after
        // training within this session).
        resumedDocCount: countMappedDocs(pp.topic_mapping),
      };

      // Training already ran (classifier stamped) → resume at the labelling step.
      const classifier = pp.classifier_id
        ? project.classifiers.find((c) => c.classifier_id === pp.classifier_id) ?? null
        : null;
      if (classifier) {
        return {
          ...base,
          currentStep: "label" as PipelineStep,
          trainedClassifier: classifier,
        };
      }

      // Reconciliation done → step 2c, otherwise the raw topic list (2b).
      return {
        ...base,
        currentStep: "topics" as PipelineStep,
        topicSubStep: pp.reconciled_topics.length > 0 ? "reconciled" : "generated",
      };
    }),

  reset: () => set(initial),
}));
