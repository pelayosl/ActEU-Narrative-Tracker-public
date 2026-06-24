import { create } from "zustand";
import type { ClassifierMetadata, Platform, SearchQuery } from "@/types/api";

// Query data carried from the pipeline into the Visualiser. Uses `languages`
// (the geographic axis the backend visualiser actually supports). Consumed by the
// Visualiser query panel once it is built — until then, setting it is a no-op handoff.
export interface VisualiserPrefill {
  topics: string[];
  date_from?: string;
  date_to?: string;
  languages: string[];
  platforms: Platform[];
}

interface VisualiserState {
  prefill: VisualiserPrefill | null;
  setPrefill: (p: VisualiserPrefill | null) => void;
}

export const useVisualiserStore = create<VisualiserState>((set) => ({
  prefill: null,
  setPrefill: (p) => set({ prefill: p }),
}));

// Map the pipeline's search query (and the freshly trained classifier, if any) to
// a Visualiser prefill. The classifier's subtopics are the most relevant topics to
// chart after labelling; otherwise fall back to the search query's topics.
export function buildVisualiserPrefill(
  searchQuery: SearchQuery | null,
  classifier: ClassifierMetadata | null,
): VisualiserPrefill {
  const topics = classifier
    ? classifier.topics.map((t) => t.topic_id)
    : (searchQuery?.topics ?? []);

  return {
    topics,
    date_from: searchQuery?.date_from,
    date_to: searchQuery?.date_to,
    languages: searchQuery?.languages ?? [],
    platforms: searchQuery?.platforms ?? [],
  };
}
