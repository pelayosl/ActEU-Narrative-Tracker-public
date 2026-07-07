/**
 * Result banner and per-topic breakdown shown after a labelling phase.
 *
 * @packageDocumentation
 */
"use client";

import type { LabellingResult } from "@/types/api";

/** Props for {@link LabellingSummary}. */
interface LabellingSummaryProps {
  /** Heading for the breakdown table. */
  title: string;
  /** Suffix for the total banner, e.g. `"labelled from original query"`. */
  bannerLabel: string;
  /** The labelling outcome to summarise. */
  result: LabellingResult;
  /** Resolve a topic id to its display name (the result is keyed by id). */
  topicName: (topicId: string) => string;
}

/**
 * Green total banner plus a per-topic breakdown table, sorted by document count
 * descending. Shown after each labelling phase; topic ids are resolved to names
 * via the `topicName` callback supplied by the caller.
 *
 * @param props - See {@link LabellingSummaryProps}.
 */
export function LabellingSummary({ title, bannerLabel, result, topicName }: LabellingSummaryProps) {
  const rows = Object.entries(result.topic_summary).sort((a, b) => b[1] - a[1]);

  return (
    <div className="space-y-4">
      <div className="rounded-md border border-green-600/30 bg-green-50 px-3 py-2 text-sm font-medium text-green-700">
        {result.total_labelled.toLocaleString()} documents {bannerLabel}
      </div>

      <div className="rounded-lg border border-border bg-white p-6">
        <h3 className="mb-4 font-semibold text-ink">{title}</h3>
        {rows.length === 0 ? (
          <p className="text-sm text-muted-foreground">No documents were labelled.</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-muted-foreground">
                <th className="pb-2 font-medium">Topic</th>
                <th className="pb-2 text-right font-medium">Documents Labelled</th>
              </tr>
            </thead>
            <tbody>
              {rows.map(([topicId, count]) => (
                <tr key={topicId} className="border-b border-border/50 last:border-0">
                  <td className="py-2 text-ink">{topicName(topicId)}</td>
                  <td className="py-2 text-right tabular-nums text-ink">
                    {count.toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
