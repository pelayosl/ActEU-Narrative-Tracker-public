"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { useSession } from "next-auth/react";
import { QueryPanel } from "@/components/visualiser/query-panel";
import { TopicEvolutionChart } from "@/components/visualiser/topic-evolution-chart";
import { LanguageBreakdown } from "@/components/visualiser/language-breakdown";
import { PlatformBreakdown } from "@/components/visualiser/platform-breakdown";
import { TopEntities } from "@/components/visualiser/top-entities";
import { DocumentsList } from "@/components/visualiser/documents-list";
import { ProjectSelectorDialog } from "@/components/projects/project-selector-dialog";
import { TOPIC_COLORS, type TopicSeriesMeta } from "@/components/visualiser/topic-colors";
import { api } from "@/lib/api-client";
import { useProjectStore } from "@/stores/project-store";
import type { Dashboard, VisualisationQuery } from "@/types/api";

export default function VisualiserPage() {
  const { data: session } = useSession();
  const activeProject = useProjectStore((s) => s.activeProject);

  // Topic metadata (value → label + colour) for the query just loaded, so charts
  // render consistent legends/colours regardless of the order the backend returns.
  const [topicMeta, setTopicMeta] = useState<TopicSeriesMeta[]>([]);

  const load = useMutation({
    mutationFn: (vars: { query: VisualisationQuery; topicLabels: Record<string, string> }) =>
      api.loadDashboard(vars.query, activeProject?.project_id, session?.accessToken),
  });

  function handleLoad(query: VisualisationQuery, topicLabels: Record<string, string>) {
    setTopicMeta(
      query.topics.map((value, i) => ({
        value,
        label: topicLabels[value] ?? value,
        color: TOPIC_COLORS[i % TOPIC_COLORS.length],
      })),
    );
    load.mutate({ query, topicLabels });
  }

  const dashboard: Dashboard | undefined = load.data;

  if (!activeProject) {
    return <ProjectSelectorDialog />;
  }

  return (
    <div className="grid grid-cols-[320px_1fr] gap-6">
      <QueryPanel onLoad={handleLoad} loading={load.isPending} />

      <div className="space-y-6">
        {load.isError && (
          <div role="alert" className="rounded-md border border-acteu-red/30 bg-acteu-red/5 p-3 text-sm text-acteu-red">
            Could not load the visualisation. Please try again.
          </div>
        )}

        {!dashboard && !load.isPending && !load.isError && (
          <div className="rounded-lg border border-border bg-white p-12 text-center text-muted-foreground">
            Select at least one topic and a timespan to begin.
          </div>
        )}

        {load.isPending && (
          <div className="rounded-lg border border-border bg-white p-12 text-center text-muted-foreground">
            Loading visualisation…
          </div>
        )}

        {dashboard && !load.isPending && (
          <>
            <TopicEvolutionChart data={dashboard.topic_evolution} topics={topicMeta} />
            <LanguageBreakdown data={dashboard.topics_by_language} topics={topicMeta} />
            <PlatformBreakdown data={dashboard.topics_by_platform} topics={topicMeta} />
            <TopEntities data={dashboard.top_entities} topics={topicMeta} />
            <DocumentsList data={dashboard.relevant_documents} topics={topicMeta} />
          </>
        )}
      </div>
    </div>
  );
}
