"use client";

import type { DocumentSummary } from "@/types/api";

export function DocumentCard({ doc }: { doc: DocumentSummary }) {
  return (
    <article className="rounded-md border border-border bg-white p-4">
      <div className="mb-2 flex items-center gap-2 text-xs">
        <span className="rounded bg-bg px-2 py-0.5 font-medium uppercase">{doc.platform}</span>
        <span className="text-muted-foreground">{doc.country}</span>
        <span className="text-muted-foreground">·</span>
        <span className="text-muted-foreground">{new Date(doc.date).toLocaleDateString()}</span>
      </div>
      <h3 className="font-medium text-ink">{doc.headline}</h3>
      <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">{doc.excerpt}</p>
    </article>
  );
}
