"use client";

import { useMemo } from "react";
import { FileText } from "lucide-react";
import { PlatformBadge } from "@/components/pipeline/platform-badge";
import type { DocumentPreview } from "@/types/api";
import type { TopicSeriesMeta } from "./topic-colors";

interface DocumentsListProps {
  data: DocumentPreview[];
  topics: TopicSeriesMeta[];
}

// The relevant documents are a confidence-weighted stratified sample across the
// query topics (computed server-side), already sorted by relevance descending.
// Each row is tagged with the topic it represents — the same document may appear
// under more than one topic, so the tag is what distinguishes the rows.
export function DocumentsList({ data, topics }: DocumentsListProps) {
  const meta = useMemo(() => new Map(topics.map((t) => [t.value, t])), [topics]);

  return (
    <section className="rounded-lg border border-border bg-white p-6">
      <h2 className="mb-1 flex items-center gap-2 font-semibold text-ink">
        <FileText className="h-4 w-4 text-acteu-red" />
        Relevant Documents
      </h2>
      <p className="mb-4 text-sm text-muted-foreground">
        A stratified sample across your topics, ranked by relevance.
      </p>

      {data.length === 0 ? (
        <p className="py-8 text-center text-sm text-muted-foreground">
          No documents matched these parameters.
        </p>
      ) : (
        <ul className="space-y-3">
          {data.map((doc, i) => {
            const topic = meta.get(doc.topic);
            return (
              <li key={`${doc.doc_id}-${doc.topic}-${i}`} className="rounded-md border border-border p-3">
                <div className="mb-2 flex flex-wrap items-center gap-2 text-xs">
                  {topic && (
                    <span className="inline-flex items-center gap-1.5 rounded-md px-2 py-0.5 font-medium text-white" style={{ backgroundColor: topic.color }}>
                      {topic.label}
                    </span>
                  )}
                  <PlatformBadge platform={doc.platform} />
                  <span className="uppercase text-muted-foreground">{doc.language}</span>
                  <span className="text-muted-foreground">·</span>
                  <span className="text-muted-foreground">
                    {doc.date ? new Date(doc.date).toLocaleDateString() : "Unknown date"}
                  </span>
                  <span className="ml-auto tabular-nums text-muted-foreground">
                    relevance {doc.relevance_score.toFixed(2)}
                  </span>
                </div>
                <p className="text-sm text-ink">{doc.excerpt}</p>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
