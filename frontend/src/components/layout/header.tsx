"use client";

import { PanelLeftOpen } from "lucide-react";
import { useProjectStore } from "@/stores/project-store";
import { useUiStore } from "@/stores/ui-store";

export function Header() {
  const activeProject = useProjectStore((s) => s.activeProject);
  const sidebarOpen = useUiStore((s) => s.sidebarOpen);
  const toggleSidebar = useUiStore((s) => s.toggleSidebar);

  return (
    <header className="flex h-14 items-center gap-4 border-b border-border bg-white px-6">
      {!sidebarOpen && (
        <button
          type="button"
          onClick={toggleSidebar}
          className="rounded-md p-1 text-ink transition-colors hover:bg-bg"
          aria-label="Show sidebar"
        >
          <PanelLeftOpen className="h-5 w-5" />
        </button>
      )}
      {activeProject && (
        <div className="text-sm text-muted-foreground">
          Active project: <span className="font-medium text-ink">{activeProject.name}</span>
        </div>
      )}
    </header>
  );
}
