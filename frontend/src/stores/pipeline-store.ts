import { create } from "zustand";
import type { ClassifierMetadata, SearchQuery, SearchResult, Topic } from "@/types/api";

export type PipelineStep = "search" | "topics" | "label";
export type TopicSubStep = "generating" | "generated" | "reconciling" | "reconciled";

// Generation-era ids a topic resolves to in the backend topic_mapping. A merged
// topic carries its constituents' ids in origin_topic_ids; a raw one uses its own
// id. Kept in sync with the backend (llm_client._generation_ids / training task).
function generationIds(topic: Topic): string[] {
  return topic.origin_topic_ids.length > 0 ? topic.origin_topic_ids : [topic.topic_id];
}

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

  setStep: (step: PipelineStep) => void;
  setTopicSubStep: (s: TopicSubStep | null) => void;
  setSearchQuery: (q: SearchQuery) => void;
  setSearchResult: (r: SearchResult) => void;
  setGeneratedTopics: (topics: Topic[]) => void;
  setReconciledTopics: (topics: Topic[]) => void;
  setGenerationJobId: (id: string | null) => void;
  setReconciliationJobId: (id: string | null) => void;
  setTrainedClassifier: (c: ClassifierMetadata) => void;

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
};

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

  reset: () => set(initial),
}));
