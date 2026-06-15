"use client";

import * as React from "react";
import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useSession } from "next-auth/react";
import { Plus, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { api } from "@/lib/api-client";
import { cn } from "@/lib/utils";
import { useProjectStore } from "@/stores/project-store";
import { useVisualiserStore } from "@/stores/visualiser-store";
import type { Platform, VisualisationQuery } from "@/types/api";

const PLATFORMS: { label: string; value: Platform }[] = [
  { label: "Twitter", value: "twitter" },
  { label: "Telegram", value: "telegram" },
  { label: "Online Media", value: "media" },
];

// Topics are capped so the relevant-documents sample can guarantee each topic a slot.
const MAX_TOPICS = 5;
const DEFAULT_SAMPLE_SIZE = 30;

function Pill({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      className={cn(
        "rounded-md border px-3 py-1 text-sm font-medium transition-colors",
        active
          ? "border-acteu-red bg-acteu-red text-white"
          : "border-border bg-white text-ink hover:bg-bg",
      )}
    >
      {children}
    </button>
  );
}

export interface QueryPanelProps {
  // Called on "Load Visualisation". topicLabels maps each submitted topic value to
  // its display name so the charts can render readable legends.
  onLoad: (query: VisualisationQuery, topicLabels: Record<string, string>) => void;
  loading?: boolean;
}

export function QueryPanel({ onLoad, loading = false }: QueryPanelProps) {
  const { data: session } = useSession();
  const activeProject = useProjectStore((s) => s.activeProject);
  const prefill = useVisualiserStore((s) => s.prefill);

  const [topics, setTopics] = useState<string[]>([]);
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [languages, setLanguages] = useState<string[]>([]);
  const [platforms, setPlatforms] = useState<string[]>([]);
  const [sampleSize, setSampleSize] = useState(DEFAULT_SAMPLE_SIZE);

  // Topic facets from the DB: the 3 core ACTEU topics + subtopics (document-native
  // db subtopics ∪ the project's classifier subtopics), merged server-side. Same
  // source as the pipeline search form.
  const { data: topicFacets } = useQuery({
    queryKey: ["project-topics", activeProject?.project_id],
    queryFn: () => api.getProjectTopics(activeProject!.project_id, session?.accessToken),
    enabled: Boolean(session?.accessToken && activeProject?.project_id),
    staleTime: Infinity,
  });

  const topicOptions = useMemo(
    () => [...(topicFacets?.core_topics ?? []), ...(topicFacets?.subtopics ?? [])],
    [topicFacets],
  );

  const labelFor = (value: string) =>
    topicOptions.find((o) => o.value === value)?.label ?? value;

  // Seed the form from a pipeline handoff once, keeping only topics that exist in
  // this project's library.
  useEffect(() => {
    if (!prefill) return;
    setTopics(
      prefill.topics.filter((v) => topicOptions.some((o) => o.value === v)).slice(0, MAX_TOPICS),
    );
    if (prefill.date_from) setDateFrom(prefill.date_from.slice(0, 10));
    if (prefill.date_to) setDateTo(prefill.date_to.slice(0, 10));
    setLanguages(prefill.languages);
    setPlatforms(prefill.platforms);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [prefill]);

  const { data: availableLanguages = [] } = useQuery({
    queryKey: ["languages"],
    queryFn: () => api.listLanguages(session?.accessToken),
    enabled: Boolean(session?.accessToken),
    staleTime: Infinity,
  });

  const languageOptions = useMemo(() => {
    let display: Intl.DisplayNames | null = null;
    try {
      display = new Intl.DisplayNames(["en"], { type: "language" });
    } catch {
      display = null;
    }
    return availableLanguages.map((code) => ({ value: code, label: display?.of(code) ?? code }));
  }, [availableLanguages]);

  const unselectedTopics = topicOptions.filter((o) => !topics.includes(o.value));
  const atTopicLimit = topics.length >= MAX_TOPICS;
  const dateInvalid = Boolean(dateFrom) && Boolean(dateTo) && dateFrom > dateTo;
  // sample_size must be at least one slot per topic (backend apportionment assumption).
  const sampleValid = sampleSize >= topics.length;
  const canLoad =
    topics.length > 0 && Boolean(dateFrom) && Boolean(dateTo) && !dateInvalid && sampleValid && !loading;

  const toggle =
    (setList: React.Dispatch<React.SetStateAction<string[]>>) => (value: string) =>
      setList((list) =>
        list.includes(value) ? list.filter((v) => v !== value) : [...list, value],
      );

  function handleLoad() {
    if (!canLoad) return;
    const query: VisualisationQuery = {
      topics,
      date_from: `${dateFrom}T00:00:00`,
      date_to: `${dateTo}T23:59:59`,
      languages,
      platforms: platforms as Platform[],
      sample_size: sampleSize,
    };
    const topicLabels = Object.fromEntries(topics.map((v) => [v, labelFor(v)]));
    onLoad(query, topicLabels);
  }

  return (
    <aside className="space-y-5 rounded-lg border border-border bg-white p-4">
      <div>
        <h2 className="font-semibold text-ink">Parameters</h2>
        <p className="text-sm text-muted-foreground">Configure your visualisation filters.</p>
      </div>

      {/* Topics — chips + add picker */}
      <div>
        <Label>Topics</Label>
        <div className="flex flex-wrap items-center gap-2">
          {topics.map((value) => (
            <span
              key={value}
              className="inline-flex items-center gap-1 rounded-md bg-acteu-red px-3 py-1 text-sm font-medium text-white"
            >
              {labelFor(value)}
              <button
                type="button"
                onClick={() => toggle(setTopics)(value)}
                aria-label={`Remove ${labelFor(value)}`}
                className="rounded-full hover:bg-white/20"
              >
                <X className="h-3.5 w-3.5" />
              </button>
            </span>
          ))}

          {unselectedTopics.length > 0 && !atTopicLimit && (
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <button
                  type="button"
                  aria-label="Add topic"
                  className="inline-flex items-center gap-1 rounded-md border border-dashed border-border px-3 py-1 text-sm text-ink transition-colors hover:bg-bg"
                >
                  <Plus className="h-4 w-4" /> Add topic
                </button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="start" className="max-h-60 overflow-y-auto">
                {unselectedTopics.map((o) => (
                  <DropdownMenuItem key={o.value} onSelect={() => toggle(setTopics)(o.value)}>
                    {o.label}
                  </DropdownMenuItem>
                ))}
              </DropdownMenuContent>
            </DropdownMenu>
          )}
        </div>
        {atTopicLimit && (
          <p className="mt-1 text-xs text-muted-foreground">Up to {MAX_TOPICS} topics.</p>
        )}
      </div>

      {/* Date range */}
      <div className="space-y-2">
        <Label>Date Range</Label>
        <Input type="date" value={dateFrom} onChange={(e) => setDateFrom(e.target.value)} aria-label="From date" />
        <Input type="date" value={dateTo} onChange={(e) => setDateTo(e.target.value)} aria-label="To date" />
        {dateInvalid && (
          <p className="text-sm text-acteu-red">Start date cannot be later than end date.</p>
        )}
      </div>

      {/* Languages */}
      {languageOptions.length > 0 && (
        <div>
          <Label>Languages</Label>
          <div className="flex flex-wrap gap-2">
            {languageOptions.map((o) => (
              <Pill key={o.value} active={languages.includes(o.value)} onClick={() => toggle(setLanguages)(o.value)}>
                {o.label}
              </Pill>
            ))}
          </div>
        </div>
      )}

      {/* Platforms */}
      <div>
        <Label>Platforms</Label>
        <div className="flex flex-wrap gap-2">
          {PLATFORMS.map((o) => (
            <Pill key={o.value} active={platforms.includes(o.value)} onClick={() => toggle(setPlatforms)(o.value)}>
              {o.label}
            </Pill>
          ))}
        </div>
      </div>

      {/* Relevant-documents sample size */}
      <div>
        <Label htmlFor="sample-size">Documents to sample</Label>
        <Input
          id="sample-size"
          type="number"
          min={Math.max(topics.length, 1)}
          max={100}
          value={sampleSize}
          onChange={(e) => setSampleSize(Number(e.target.value))}
        />
        <p className="mt-1 text-xs text-muted-foreground">
          Total relevant documents, shared across topics by confidence.
        </p>
        {!sampleValid && (
          <p className="mt-1 text-xs text-acteu-red">
            Must be at least the number of selected topics ({topics.length}).
          </p>
        )}
      </div>

      <Button onClick={handleLoad} disabled={!canLoad} className="w-full">
        {loading ? "Loading…" : "Load Visualisation"}
      </Button>
    </aside>
  );
}
