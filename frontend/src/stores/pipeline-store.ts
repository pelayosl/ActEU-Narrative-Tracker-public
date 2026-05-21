import { create } from "zustand";
import type { ClassifierMetadata, SearchQuery, SearchResult, Topic } from "@/types/api";

export type PipelineStep = "search" | "topics" | "label";
export type TopicSubStep = "generating" | "generated" | "reconciling" | "reconciled";

interface PipelineState {
  currentStep: PipelineStep;
  topicSubStep: TopicSubStep | null;

  searchQuery: SearchQuery | null;
  searchResult: SearchResult | null;
  generatedTopics: Topic[];
  reconciledTopics: Topic[];
  trainedClassifier: ClassifierMetadata | null;

  setStep: (step: PipelineStep) => void;
  setTopicSubStep: (s: TopicSubStep | null) => void;
  setSearchQuery: (q: SearchQuery) => void;
  setSearchResult: (r: SearchResult) => void;
  setGeneratedTopics: (topics: Topic[]) => void;
  setReconciledTopics: (topics: Topic[]) => void;
  setTrainedClassifier: (c: ClassifierMetadata) => void;
  reset: () => void;
}

const initial = {
  currentStep: "search" as PipelineStep,
  topicSubStep: null,
  searchQuery: null,
  searchResult: null,
  generatedTopics: [],
  reconciledTopics: [],
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
  setTrainedClassifier: (c) => set({ trainedClassifier: c }),
  reset: () => set(initial),
}));
