"use client";

import { cn } from "@/lib/utils";
import type { DocumentSummary } from "@/types/api";
import { PlatformBadge } from "./platform-badge";

export function DocumentCard({
  doc,
  selected = false,
  onClick,
  resolveTopic = (t) => t,
}: {
  doc: DocumentSummary;
  selected?: boolean;
  onClick?: () => void;
  /** Maps a relevant_topic value to its display label (core topics arrive as slugs). */
  resolveTopic?: (topic: string) => string;
}) {
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!onClick) return;
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      onClick();
    }
  };

  return (
    <article
      onClick={onClick}
      onKeyDown={handleKeyDown}
      role={onClick ? "button" : undefined}
      tabIndex={onClick ? 0 : undefined}
      className={cn(
        "rounded-md border bg-white p-4 transition-colors",
        onClick && "cursor-pointer hover:border-acteu-red/50",
        selected ? "border-acteu-red ring-1 ring-acteu-red" : "border-border",
      )}
    >
      <div className="mb-2 flex items-center gap-2 text-xs">
        <PlatformBadge platform={doc.platform} />
        <span className="uppercase text-muted-foreground">{doc.language}</span>
        <span className="text-muted-foreground">·</span>
        <span className="text-muted-foreground">
          {doc.date ? new Date(doc.date).toLocaleDateString() : "Unknown date"}
        </span>
      </div>
      <h3 className="font-medium text-ink">{doc.headline}</h3>
      <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">{doc.excerpt}</p>
      {doc.relevant_topics.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1.5">
          {doc.relevant_topics.map((topic) => (
            <span
              key={topic}
              className="rounded-full border border-acteu-red/30 bg-acteu-red/5 px-2 py-0.5 text-xs font-medium text-acteu-red"
            >
              {resolveTopic(topic)}
            </span>
          ))}
        </div>
      )}
    </article>
  );
}
