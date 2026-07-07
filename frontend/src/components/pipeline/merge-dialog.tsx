/**
 * Dialog for naming a topic merged from several selected topics.
 *
 * @packageDocumentation
 */
"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import type { Topic } from "@/types/api";

/** Props for {@link MergeDialog}. */
interface MergeDialogProps {
  /** Whether the dialog is visible. */
  open: boolean;
  /** Callback to open/close the dialog. */
  onOpenChange: (open: boolean) => void;
  /** The selected topics being merged. */
  topics: Topic[];
  /** Confirm the merge with the chosen name and description. */
  onConfirm: (name: string, description: string) => void;
}

/**
 * Collect a name and description for a merged topic (a frontend-only operation,
 * no backend call). The fields are pre-filled from the selected topics — the
 * names joined with " + " and the first topic's description — and re-seeded each
 * time the dialog reopens with a new selection. Both fields must be non-empty to
 * confirm.
 *
 * @param props - See {@link MergeDialogProps}.
 */
export function MergeDialog({ open, onOpenChange, topics, onConfirm }: MergeDialogProps) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");

  // Re-seed the fields each time the dialog opens with a fresh selection.
  const [seededFor, setSeededFor] = useState<string>("");
  const selectionKey = topics.map((t) => t.topic_id).join(",");
  if (open && seededFor !== selectionKey) {
    setName(topics.map((t) => t.name).join(" + "));
    setDescription(topics[0]?.description ?? "");
    setSeededFor(selectionKey);
  }
  if (!open && seededFor !== "") setSeededFor("");

  const canConfirm = name.trim().length > 0 && description.trim().length > 0;

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Merge Topics</DialogTitle>
          <DialogDescription>Enter a name and description for the merged topic.</DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="space-y-1">
            <Label htmlFor="merge-name">Topic Name</Label>
            <Input
              id="merge-name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              autoFocus
            />
          </div>
          <div className="space-y-1">
            <Label htmlFor="merge-description">Description</Label>
            <textarea
              id="merge-description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              className="w-full rounded-md border border-border bg-white px-3 py-2 text-sm text-ink outline-none transition-colors focus:border-acteu-red focus:ring-1 focus:ring-acteu-red"
            />
          </div>
        </div>

        <div className="mt-4 flex justify-end gap-2">
          <Button variant="ghost" onClick={() => onOpenChange(false)}>
            Cancel
          </Button>
          <Button
            disabled={!canConfirm}
            onClick={() => {
              if (!canConfirm) return;
              onConfirm(name.trim(), description.trim());
              onOpenChange(false);
            }}
          >
            Merge Topics
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
