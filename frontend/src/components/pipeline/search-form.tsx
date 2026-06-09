"use client";

import * as React from "react";
import { useMemo, useState } from "react";
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
import type { Platform, SearchQuery } from "@/types/api";

const PLATFORMS: { label: string; value: Platform }[] = [
  { label: "Twitter", value: "twitter" },
  { label: "Telegram", value: "telegram" },
  { label: "Online Media", value: "media" },
];

// ActEU core topics submit their stored label; project subtopics submit their topic_id (UUID).
const ACTEU_TOPICS: { label: string; value: string }[] = [
  { label: "Immigration", value: "immigration" },
  { label: "Climate Change", value: "climate_change" },
  { label: "Gender Issues", value: "gender_issues" },
];

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

function Facet({
  label,
  options,
  selected,
  onToggle,
}: {
  label: string;
  options: { label: string; value: string }[];
  selected: string[];
  onToggle: (value: string) => void;
}) {
  return (
    <div>
      <Label>{label}</Label>
      <div className="flex flex-wrap gap-2">
        {options.map((o) => (
          <Pill key={o.value} active={selected.includes(o.value)} onClick={() => onToggle(o.value)}>
            {o.label}
          </Pill>
        ))}
      </div>
    </div>
  );
}

export interface SearchFormProps {
  onSubmit: (query: SearchQuery) => void;
  /** Reduced padding + no heading, for reuse inside Apply Classifier / Label Custom Query dialogs. */
  compact?: boolean;
  submitLabel?: string;
  loading?: boolean;
}

export function SearchForm({
  onSubmit,
  compact = false,
  submitLabel = "Search",
  loading = false,
}: SearchFormProps) {
  const { data: session } = useSession();
  const activeProject = useProjectStore((s) => s.activeProject);

  const [keywords, setKeywords] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [languages, setLanguages] = useState<string[]>([]);
  const [platforms, setPlatforms] = useState<string[]>([]);
  const [topics, setTopics] = useState<string[]>([]);
  const [subtopics, setSubtopics] = useState<string[]>([]);
  const [confidence, setConfidence] = useState(0); // 0 = no minimum (sent as null)

  // Languages are loaded from the DB so every option exists in at least one document.
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
    return availableLanguages.map((code) => ({
      value: code,
      label: display?.of(code) ?? code,
    }));
  }, [availableLanguages]);

  // Subtopics are the project's classifier topics (value = topic_id), sorted alphabetically.
  const subtopicOptions = useMemo(() => {
    const seen = new Map<string, string>();
    for (const classifier of activeProject?.classifiers ?? []) {
      for (const topic of classifier.topics) seen.set(topic.topic_id, topic.name);
    }
    return [...seen]
      .map(([value, label]) => ({ value, label }))
      .sort((a, b) => a.label.localeCompare(b.label));
  }, [activeProject]);

  const unselectedSubtopics = subtopicOptions.filter((o) => !subtopics.includes(o.value));

  // ISO yyyy-mm-dd strings compare lexicographically, so a plain string compare is correct here.
  const dateInvalid = Boolean(dateFrom) && Boolean(dateTo) && dateFrom > dateTo;

  const toggle =
    (setList: React.Dispatch<React.SetStateAction<string[]>>) => (value: string) =>
      setList((list) =>
        list.includes(value) ? list.filter((v) => v !== value) : [...list, value],
      );

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (dateInvalid || loading) return;

    const query: SearchQuery = {
      keywords: keywords
        .split(",")
        .map((k) => k.trim())
        .filter(Boolean),
      languages,
      platforms: platforms as Platform[],
      topics,
      subtopics,
      confidence_threshold: confidence > 0 ? confidence : null,
      ...(dateFrom ? { date_from: `${dateFrom}T00:00:00` } : {}),
      ...(dateTo ? { date_to: `${dateTo}T23:59:59` } : {}),
    };
    onSubmit(query);
  }

  return (
    <form
      onSubmit={handleSubmit}
      className={cn(
        "space-y-5 rounded-lg border border-border bg-white",
        compact ? "p-4" : "p-6",
      )}
    >
      {!compact && <h2 className="text-lg font-semibold text-ink">Search Parameters</h2>}

      <div>
        <Label htmlFor="keywords">Keywords</Label>
        <Input
          id="keywords"
          value={keywords}
          onChange={(e) => setKeywords(e.target.value)}
          placeholder="e.g. Rubiales, kiss, FIFA"
        />
        <p className="mt-1 text-xs text-muted-foreground">Separate multiple keywords with commas</p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
        <div>
          <Label htmlFor="date-from">From Date</Label>
          <Input
            id="date-from"
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
          />
        </div>
        <div>
          <Label htmlFor="date-to">To Date</Label>
          <Input
            id="date-to"
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
          />
        </div>
      </div>
      {dateInvalid && (
        <p className="text-sm text-acteu-red">Start date cannot be later than end date.</p>
      )}

      {languageOptions.length > 0 && (
        <Facet
          label="Languages"
          options={languageOptions}
          selected={languages}
          onToggle={toggle(setLanguages)}
        />
      )}
      <Facet label="Platforms" options={PLATFORMS} selected={platforms} onToggle={toggle(setPlatforms)} />
      <Facet label="ActEU topics" options={ACTEU_TOPICS} selected={topics} onToggle={toggle(setTopics)} />

      <div>
        <Label>Subtopics</Label>
        <div className="flex flex-wrap items-center gap-2">
          {subtopics.map((id) => {
            const opt = subtopicOptions.find((o) => o.value === id);
            return (
              <span
                key={id}
                className="inline-flex items-center gap-1 rounded-md bg-acteu-red px-3 py-1 text-sm font-medium text-white"
              >
                {opt?.label ?? id}
                <button
                  type="button"
                  onClick={() => toggle(setSubtopics)(id)}
                  aria-label={`Remove ${opt?.label ?? id}`}
                  className="rounded-full hover:bg-white/20"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              </span>
            );
          })}

          {subtopicOptions.length === 0 ? (
            <p className="text-xs text-muted-foreground">
              No subtopics available — train a classifier in this project to create some.
            </p>
          ) : (
            unselectedSubtopics.length > 0 && (
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <button
                    type="button"
                    aria-label="Add subtopic"
                    className="inline-flex items-center gap-1 rounded-md border border-dashed border-border px-3 py-1 text-sm text-ink transition-colors hover:bg-bg"
                  >
                    <Plus className="h-4 w-4" /> Add
                  </button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="start" className="max-h-60 overflow-y-auto">
                  {unselectedSubtopics.map((o) => (
                    <DropdownMenuItem key={o.value} onSelect={() => toggle(setSubtopics)(o.value)}>
                      {o.label}
                    </DropdownMenuItem>
                  ))}
                </DropdownMenuContent>
              </DropdownMenu>
            )
          )}
        </div>
      </div>

      <div>
        <Label htmlFor="confidence">
          Minimum confidence{confidence > 0 ? `: ${Math.round(confidence * 100)}%` : ""}
        </Label>
        <input
          id="confidence"
          type="range"
          min={0}
          max={1}
          step={0.05}
          value={confidence}
          onChange={(e) => setConfidence(Number(e.target.value))}
          className="w-full accent-acteu-red"
        />
        <p className="mt-1 text-xs text-muted-foreground">
          {confidence > 0
            ? "Only documents whose topic/subtopic confidence is at least this value."
            : "No minimum — include all matches."}
        </p>
      </div>

      <Button type="submit" size="lg" className="w-full" disabled={dateInvalid || loading}>
        {loading ? "Searching…" : submitLabel}
      </Button>
    </form>
  );
}
