/**
 * Store for the query handed off from the pipeline to the Visualiser.
 *
 * When a user finishes labelling in the pipeline, the search parameters (and the
 * trained classifier's topics) are stashed here so the Visualiser can open
 * pre-populated instead of forcing the user to re-enter the query.
 *
 * @packageDocumentation
 */
import { create } from "zustand";
import type { ClassifierMetadata, Platform, SearchQuery } from "@/types/api";

/**
 * Query data carried from the pipeline into the Visualiser.
 *
 * Uses `languages` (the geographic axis the backend visualiser actually
 * supports). Consumed by the Visualiser query panel to pre-fill its controls.
 */
export interface VisualiserPrefill {
  topics: string[];
  date_from?: string;
  date_to?: string;
  languages: string[];
  platforms: Platform[];
}

/** State shape of the visualiser handoff store. */
interface VisualiserState {
  /** Pending prefill to apply on the next Visualiser open, or `null`. */
  prefill: VisualiserPrefill | null;
  /** Stash (or clear) the prefill to hand to the Visualiser. */
  setPrefill: (p: VisualiserPrefill | null) => void;
}

/** Zustand hook holding the pipeline → Visualiser query handoff. */
export const useVisualiserStore = create<VisualiserState>((set) => ({
  prefill: null,
  setPrefill: (p) => set({ prefill: p }),
}));

/**
 * Build a Visualiser prefill from the pipeline's search query and classifier.
 *
 * The classifier's subtopics are the most relevant topics to chart after
 * labelling, so they are preferred; when no classifier was trained, the search
 * query's topics are used. Dates, languages and platforms come from the query.
 *
 * @param searchQuery - The pipeline's search query, or `null` if unavailable.
 * @param classifier - The freshly trained classifier, or `null` if none.
 * @returns A {@link VisualiserPrefill} ready to stash via `setPrefill`.
 */
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
