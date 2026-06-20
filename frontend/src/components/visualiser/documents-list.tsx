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

// The relevant documents are a document-count-weighted stratified sample across the
// query topics (computed server-side, with platforms interleaved per topic). They are
// grouped here by topic so each topic's examples are shown together, ranked by
// relevance within the group. The same document may appear under more than one topic.
export function DocumentsList({ data, topics }: DocumentsListProps) {
  // Group documents by topic, following the query's topic order; documents within a
  // group keep the relevance order the backend already applied. Topics with no
  // matching documents (and any unknown topics) are handled gracefully.
  const groups = useMemo(() => {
    const byTopic = new Map<string, DocumentPreview[]>();
    for (const doc of data) {
      const list = byTopic.get(doc.topic) ?? [];
      list.push(doc);
      byTopic.set(doc.topic, list);
    }

    const ordered: { value: string; meta?: TopicSeriesMeta; docs: DocumentPreview[] }[] = [];
    for (const t of topics) {
      const docs = byTopic.get(t.value);
      if (docs) {
        ordered.push({ value: t.value, meta: t, docs });
        byTopic.delete(t.value);
      }
    }
    // Any topics not present in the legend metadata are appended last.
    for (const [value, docs] of byTopic) {
      ordered.push({ value, docs });
    }
    return ordered;
  }, [data, topics]);

  return (
    <section className="rounded-lg border border-border bg-white p-6">
      <h2 className="mb-1 flex items-center gap-2 font-semibold text-ink">
        <FileText className="h-4 w-4 text-acteu-red" />
        Relevant Documents
      </h2>
      <p className="mb-4 text-sm text-muted-foreground">
        A stratified sample grouped by topic, ranked by relevance.
      </p>

      {data.length === 0 ? (
        <p className="py-8 text-center text-sm text-muted-foreground">
          No documents matched these parameters.
        </p>
      ) : (
        <div className="space-y-6">
          {groups.map((group) => (
            <div key={group.value}>
              <h3 className="mb-2 flex items-center gap-2 text-sm font-medium text-ink">
                <span
                  className="inline-flex items-center gap-1.5 rounded-md px-2 py-0.5 font-medium text-white"
                  style={{ backgroundColor: group.meta?.color ?? "#64748b" }}
                >
                  {group.meta?.label ?? group.value}
                </span>
                <span className="tabular-nums text-muted-foreground">
                  {group.docs.length}
                </span>
              </h3>
              <ul className="space-y-3">
                {group.docs.map((doc, i) => (
                  <li key={`${doc.doc_id}-${doc.topic}-${i}`} className="rounded-md border border-border p-3">
                    <div className="mb-2 flex flex-wrap items-center gap-2 text-xs">
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
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
