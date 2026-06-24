"use client";

import { useEffect, useMemo, useState } from "react";
import { Network } from "lucide-react";
import type { TopicEntities } from "@/types/api";
import type { TopicSeriesMeta } from "./topic-colors";

interface TopEntitiesProps {
  data: TopicEntities[];
  topics: TopicSeriesMeta[];
}

const MAX_ENTITIES = 10;

// Top entities per topic, ranked by PageRank (shown as "relevance"). The user picks
// which topic/subtopic to inspect from a dropdown inside the card.
export function TopEntities({ data, topics }: TopEntitiesProps) {
  // Only offer topics that actually have an entities entry.
  const options = useMemo(
    () => topics.filter((t) => data.some((d) => d.topic === t.value)),
    [topics, data],
  );

  const [selected, setSelected] = useState<string>(options[0]?.value ?? "");

  // Keep the selection valid when a new dashboard loads.
  useEffect(() => {
    if (options.length > 0 && !options.some((o) => o.value === selected)) {
      setSelected(options[0].value);
    }
  }, [options, selected]);

  const entities = useMemo(() => {
    const entry = data.find((d) => d.topic === selected);
    return (entry?.entities ?? []).slice(0, MAX_ENTITIES);
  }, [data, selected]);

  const maxScore = entities[0]?.score ?? 0;

  return (
    <section className="rounded-lg border border-border bg-white p-6">
      <div className="mb-1 flex flex-wrap items-center justify-between gap-3">
        <h2 className="flex items-center gap-2 font-semibold text-ink">
          <Network className="h-4 w-4 text-acteu-red" />
          Top Entities
        </h2>
        {options.length > 0 && (
          <select
            value={selected}
            onChange={(e) => setSelected(e.target.value)}
            aria-label="Select topic"
            className="h-9 max-w-[16rem] rounded-md border border-border bg-white px-3 text-sm text-ink outline-none focus:border-acteu-red focus:ring-1 focus:ring-acteu-red"
          >
            {options.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
        )}
      </div>
      <p className="mb-4 text-sm text-muted-foreground">
        People, places, and organisations most central to this topic. The relevance score
        (0–1) reflects how connected each one is within the topic — higher means more central.
      </p>

      {entities.length === 0 ? (
        <p className="py-8 text-center text-sm text-muted-foreground">
          No entities for this topic.
        </p>
      ) : (
        <>
          <div className="mb-2 flex items-center gap-3 border-b border-border pb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
            <span className="w-5 text-right">#</span>
            <span className="flex-1">Entity</span>
            <span className="w-24 text-center">Relevance</span>
            <span className="w-16 text-right">Score</span>
          </div>
          <ol className="space-y-2">
          {entities.map((e, i) => (
            <li key={e.entity} className="flex items-center gap-3">
              <span className="w-5 text-right text-sm tabular-nums text-muted-foreground">
                {i + 1}
              </span>
              <span className="flex-1 truncate text-sm font-medium text-ink" title={e.entity}>
                {e.entity}
              </span>
              {/* Relevance bar, scaled to the top entity for the selected topic. */}
              <span className="h-2 w-24 overflow-hidden rounded-full bg-bg" aria-hidden>
                <span
                  className="block h-full rounded-full bg-acteu-red"
                  style={{ width: `${maxScore > 0 ? (e.score / maxScore) * 100 : 0}%` }}
                />
              </span>
              <span className="w-16 text-right text-sm tabular-nums text-muted-foreground">
                {e.score.toFixed(4)}
              </span>
            </li>
          ))}
          </ol>
        </>
      )}
    </section>
  );
}
