/**
 * Global store for transient UI chrome state (the sidebar).
 *
 * @packageDocumentation
 */
import { create } from "zustand";

/** State shape of the UI store. */
interface UiState {
  /** Whether the sidebar is currently expanded/visible. */
  sidebarOpen: boolean;
  /** True when the viewport is below the sidebar breakpoint (overlay mode). */
  isNarrow: boolean;
  /** Flip the sidebar between open and closed. */
  toggleSidebar: () => void;
  /** Explicitly open or close the sidebar. */
  setSidebarOpen: (open: boolean) => void;
  /** Record whether the viewport is in the narrow (overlay) regime. */
  setNarrow: (narrow: boolean) => void;
}

/** Zustand hook exposing sidebar visibility and viewport width state. */
export const useUiStore = create<UiState>((set) => ({
  sidebarOpen: true,
  isNarrow: false,
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
  setNarrow: (narrow) => set({ isNarrow: narrow }),
}));
