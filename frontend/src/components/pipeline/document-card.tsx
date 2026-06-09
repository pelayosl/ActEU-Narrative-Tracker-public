"use client";

import { cn } from "@/lib/utils";
import type { DocumentSummary } from "@/types/api";

export function DocumentCard({
  doc,
  selected = false,
  onClick,
}: {
  doc: DocumentSummary;
  selected?: boolean;
  onClick?: () => void;
}) {
  return (
    <article
      onClick={onClick}
      className={cn(
        "rounded-md border bg-white p-4 transition-colors",
        onClick && "cursor-pointer hover:border-acteu-red/50",
        selected ? "border-acteu-red ring-1 ring-acteu-red" : "border-border",
      )}
    >
      <div className="mb-2 flex items-center gap-2 text-xs">
        <span className="rounded bg-bg px-2 py-0.5 font-medium uppercase">{doc.platform}</span>
        <span className="uppercase text-muted-foreground">{doc.language}</span>
        <span className="text-muted-foreground">·</span>
        <span className="text-muted-foreground">{new Date(doc.date).toLocaleDateString()}</span>
      </div>
      <h3 className="font-medium text-ink">{doc.headline}</h3>
      <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">{doc.excerpt}</p>
    </article>
  );
}
