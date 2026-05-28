"use client";

import { QueryPanel } from "@/components/visualizer/query-panel";
import { TopicEvolutionChart } from "@/components/visualizer/topic-evolution-chart";
import { CountryBreakdown } from "@/components/visualizer/country-breakdown";
import { ActorsTable } from "@/components/visualizer/actors-table";
import { DocumentsList } from "@/components/visualizer/documents-list";
import { ProjectSelectorDialog } from "@/components/projects/project-selector-dialog";
import { useProjectStore } from "@/stores/project-store";
import { useState } from "react";

export default function VisualizerPage() {
  const activeProject = useProjectStore((s) => s.activeProject);
  const [loaded, setLoaded] = useState(false);

  if (!activeProject) {
    return <ProjectSelectorDialog />;
  }

  return (
    <div className="grid grid-cols-[320px_1fr] gap-6">
      <QueryPanel onLoad={() => setLoaded(true)} />
      <div className="space-y-6">
        {!loaded ? (
          <div className="rounded-lg border border-border bg-white p-12 text-center text-muted-foreground">
            Select at least one topic and a timespan to begin.
          </div>
        ) : (
          <>
            <TopicEvolutionChart />
            <CountryBreakdown />
            <ActorsTable />
            <DocumentsList />
          </>
        )}
      </div>
    </div>
  );
}
