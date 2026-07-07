/**
 * Global store holding the currently selected project.
 *
 * The active project scopes the pipeline, classifiers and visualiser to one
 * project; it is chosen in the project selector and read across the app.
 *
 * @packageDocumentation
 */
import { create } from "zustand";
import type { Project } from "@/types/api";

/** State shape of the active-project store. */
interface ProjectState {
  /** The project currently in focus, or `null` when none is selected. */
  activeProject: Project | null;
  /** Set (or clear) the active project. */
  setActiveProject: (project: Project | null) => void;
}

/** Zustand hook exposing the active project and its setter. */
export const useProjectStore = create<ProjectState>((set) => ({
  activeProject: null,
  setActiveProject: (project) => set({ activeProject: project }),
}));
