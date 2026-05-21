"use client";

import { Pencil, Trash2 } from "lucide-react";
import type { Topic } from "@/types/api";

// TODO: pencil → inline editable name + description (both non-empty to confirm).
// trash → confirmation modal. For reconciled topics, delete = split back into origin_topic_ids.
// checkbox (raw topics only) → used for manual merging.
export function TopicCard({ topic, reconciled }: { topic: Topic; reconciled: boolean }) {
  return (
    <li className="flex items-start gap-3 rounded-md border border-border bg-white p-4">
      {!reconciled && <input type="checkbox" className="mt-1" />}
      <div className="flex-1">
        <div className="font-medium text-ink">{topic.name}</div>
        <div className="text-sm text-muted-foreground">{topic.description}</div>
        {reconciled && topic.origin_topic_ids.length > 0 && (
          <div className="mt-1 text-xs text-muted-foreground">
            Fuses: {topic.origin_topic_ids.join(", ")}
          </div>
        )}
      </div>
      <button className="text-muted-foreground hover:text-ink" aria-label="Edit topic">
        <Pencil className="h-4 w-4" />
      </button>
      <button className="text-muted-foreground hover:text-acteu-red" aria-label="Delete topic">
        <Trash2 className="h-4 w-4" />
      </button>
    </li>
  );
}
