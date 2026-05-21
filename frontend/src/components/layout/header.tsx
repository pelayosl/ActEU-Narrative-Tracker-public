"use client";

import { useProjectStore } from "@/stores/project-store";

export function Header() {
  const activeProject = useProjectStore((s) => s.activeProject);

  return (
    <header className="flex h-14 items-center border-b border-border bg-white px-6">
      {activeProject && (
        <div className="text-sm text-muted-foreground">
          Active project: <span className="font-medium text-ink">{activeProject.name}</span>
        </div>
      )}
    </header>
  );
}
