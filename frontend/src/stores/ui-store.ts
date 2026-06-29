import { create } from "zustand";

interface UiState {
  sidebarOpen: boolean;
  /** True when the viewport is below the sidebar breakpoint (overlay mode). */
  isNarrow: boolean;
  toggleSidebar: () => void;
  setSidebarOpen: (open: boolean) => void;
  setNarrow: (narrow: boolean) => void;
}

export const useUiStore = create<UiState>((set) => ({
  sidebarOpen: true,
  isNarrow: false,
  toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
  setNarrow: (narrow) => set({ isNarrow: narrow }),
}));
