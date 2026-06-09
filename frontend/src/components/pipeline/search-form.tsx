"use client";

import * as React from "react";
import { useMemo, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { cn } from "@/lib/utils";
import { useProjectStore } from "@/stores/project-store";
import type { Platform, SearchQuery } from "@/types/api";

// The "Countries" facet shows country names but submits ISO language codes, because the
// backend SearchQuery filters on `documents.language` (there is no country filter). The
// dataset cannot reliably attribute country, so language is the geographic axis throughout.
const COUNTRIES: { label: string; value: string }[] = [
  { label: "Spain", value: "es" },
  { label: "France", value: "fr" },
  { label: "Germany", value: "de" },
  { label: "Italy", value: "it" },
  { label: "Poland", value: "pl" },
  { label: "Netherlands", value: "nl" },
  { label: "Sweden", value: "sv" },
  { label: "Hungary", value: "hu" },
  { label: "Portugal", value: "pt" },
  { label: "Greece", value: "el" },
];

const PLATFORMS: { label: string; value: Platform }[] = [
  { label: "Twitter", value: "twitter" },
  { label: "Telegram", value: "telegram" },
  { label: "Online Media", value: "media" },
];

// Core topics submit their stored label; project subtopics submit their topic_id (UUID).
const TOPICS: { label: string; value: string }[] = [
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
  /** Reduced padding + no heading, for reuse inside the Apply Classifier / Label Custom Query dialogs. */
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
  const activeProject = useProjectStore((s) => s.activeProject);

  const [keywords, setKeywords] = useState("");
  const [dateFrom, setDateFrom] = useState("");
  const [dateTo, setDateTo] = useState("");
  const [countries, setCountries] = useState<string[]>([]);
  const [platforms, setPlatforms] = useState<string[]>([]);
  const [topics, setTopics] = useState<string[]>([]);
  const [subtopics, setSubtopics] = useState<string[]>([]);

  // Subtopics are the project's classifier topics (value = topic_id). The data model has no
  // link from a subtopic back to a core topic, so they are not filtered by the selected topics.
  const subtopicOptions = useMemo(() => {
    const seen = new Map<string, string>();
    for (const classifier of activeProject?.classifiers ?? []) {
      for (const topic of classifier.topics) seen.set(topic.topic_id, topic.name);
    }
    return [...seen].map(([value, label]) => ({ value, label }));
  }, [activeProject]);

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
      languages: countries,
      platforms: platforms as Platform[],
      topics,
      subtopics,
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

      <Facet label="Countries" options={COUNTRIES} selected={countries} onToggle={toggle(setCountries)} />
      <Facet label="Platforms" options={PLATFORMS} selected={platforms} onToggle={toggle(setPlatforms)} />
      <Facet label="Topics" options={TOPICS} selected={topics} onToggle={toggle(setTopics)} />

      <div>
        <Label>Subtopics</Label>
        {subtopicOptions.length > 0 ? (
          <div className="flex flex-wrap gap-2">
            {subtopicOptions.map((o) => (
              <Pill
                key={o.value}
                active={subtopics.includes(o.value)}
                onClick={() => toggle(setSubtopics)(o.value)}
              >
                {o.label}
              </Pill>
            ))}
          </div>
        ) : (
          <p className="text-xs text-muted-foreground">
            No subtopics available — train a classifier in this project to create some.
          </p>
        )}
      </div>

      <Button type="submit" size="lg" className="w-full" disabled={dateInvalid || loading}>
        {loading ? "Searching…" : submitLabel}
      </Button>
    </form>
  );
}
