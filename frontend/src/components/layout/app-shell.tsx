"use client";

import { useEffect } from "react";
import { Sidebar } from "./sidebar";
import { Header } from "./header";
import { useUiStore } from "@/stores/ui-store";

// Below Tailwind's `lg` breakpoint (1024px) the sidebar can no longer sit
// alongside the content without forcing a horizontal scrollbar, so it switches
// to an overlay that hovers over the content instead of pushing it aside.
const NARROW_QUERY = "(max-width: 1023px)";

export function AppShell({ children }: { children: React.ReactNode }) {
  const isNarrow = useUiStore((s) => s.isNarrow);
  const sidebarOpen = useUiStore((s) => s.sidebarOpen);
  const setNarrow = useUiStore((s) => s.setNarrow);
  const setSidebarOpen = useUiStore((s) => s.setSidebarOpen);

  // Track the viewport width: minimise the sidebar when narrow, restore it when
  // wide. Reopening while narrow is handled by the overlay rendering below.
  useEffect(() => {
    const mql = window.matchMedia(NARROW_QUERY);
    const apply = (narrow: boolean) => {
      setNarrow(narrow);
      setSidebarOpen(!narrow);
    };
    apply(mql.matches);
    const handler = (e: MediaQueryListEvent) => apply(e.matches);
    mql.addEventListener("change", handler);
    return () => mql.removeEventListener("change", handler);
  }, [setNarrow, setSidebarOpen]);

  // Close the overlay sidebar with Escape for keyboard accessibility.
  useEffect(() => {
    if (!isNarrow || !sidebarOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setSidebarOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [isNarrow, sidebarOpen, setSidebarOpen]);

  return (
    <div className="flex min-h-screen bg-bg">
      <Sidebar />
      {isNarrow && sidebarOpen && (
        <button
          type="button"
          aria-label="Close sidebar"
          onClick={() => setSidebarOpen(false)}
          className="fixed inset-0 z-30 bg-black/40"
        />
      )}
      <div className="flex min-w-0 flex-1 flex-col">
        <Header />
        <main className="flex-1 p-6">{children}</main>
      </div>
    </div>
  );
}
