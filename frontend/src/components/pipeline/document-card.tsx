"use client";

import { cn } from "@/lib/utils";
import type { DocumentSummary } from "@/types/api";
import { PlatformBadge } from "./platform-badge";

export function DocumentCard({
  doc,
  selected = false,
  onClick,
}: {
  doc: DocumentSummary;
  selected?: boolean;
  onClick?: () => void;
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
        <span className="text-muted-foreground">{new Date(doc.date).toLocaleDateString()}</span>
      </div>
      <h3 className="font-medium text-ink">{doc.headline}</h3>
      <p className="mt-1 line-clamp-2 text-sm text-muted-foreground">{doc.excerpt}</p>
    </article>
  );
}
