"use client";

import { Button } from "@/components/ui/button";

// TODO: topics picker (+ icon opens library: 3 core + project's classifier topics),
// date range, countries multi-select, platforms multi-select.
// On "Load Visualisation" → api.loadDashboard. Panel stays visible during reloads.
export function QueryPanel({ onLoad }: { onLoad: () => void }) {
  return (
    <aside className="space-y-4 rounded-lg border border-border bg-white p-4">
      <h2 className="font-semibold text-ink">Query</h2>
      <p className="text-sm text-muted-foreground">Parameters placeholder.</p>
      <Button onClick={onLoad} className="w-full">Load Visualisation</Button>
    </aside>
  );
}
