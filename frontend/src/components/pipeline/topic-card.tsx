"use client";

import { useState } from "react";
import { Check, Pencil, Trash2, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import type { Topic } from "@/types/api";

interface TopicCardProps {
  topic: Topic;
  index: number;
  reconciled: boolean;
  selected?: boolean;
  onToggleSelect?: () => void;
  fusesLabel?: string;
  onEdit: (name: string, description: string) => void;
  onDelete: () => void;
}

export function TopicCard({
  topic,
  index,
  reconciled,
  selected = false,
  onToggleSelect,
  fusesLabel,
  onEdit,
  onDelete,
}: TopicCardProps) {
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(topic.name);
  const [description, setDescription] = useState(topic.description);
  const [confirmDelete, setConfirmDelete] = useState(false);

  const canConfirm = name.trim().length > 0 && description.trim().length > 0;

  function startEdit() {
    setName(topic.name);
    setDescription(topic.description);
    setEditing(true);
  }

  function confirmEdit() {
    if (!canConfirm) return;
    onEdit(name.trim(), description.trim());
    setEditing(false);
  }

  return (
    <li className="flex items-start gap-3 rounded-md border border-border bg-white p-4">
      {!reconciled && (
        <input
          type="checkbox"
          className="mt-1 accent-acteu-red"
          checked={selected}
          onChange={onToggleSelect}
          aria-label={`Select topic ${topic.name}`}
        />
      )}

      <span className="mt-0.5 text-sm font-semibold text-muted-foreground">{index}</span>

      <div className="flex-1">
        {editing ? (
          <div className="space-y-2">
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Topic name"
              aria-label="Topic name"
              autoFocus
            />
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Description"
              aria-label="Topic description"
              rows={2}
              className="w-full rounded-md border border-border bg-white px-3 py-2 text-sm text-ink outline-none transition-colors focus:border-acteu-red focus:ring-1 focus:ring-acteu-red"
            />
            <div className="flex gap-2">
              <button
                onClick={confirmEdit}
                disabled={!canConfirm}
                className="text-acteu-red hover:text-acteu-red-hover disabled:cursor-not-allowed disabled:opacity-40"
                aria-label="Confirm edit"
              >
                <Check className="h-4 w-4" />
              </button>
              <button
                onClick={() => setEditing(false)}
                className="text-muted-foreground hover:text-ink"
                aria-label="Cancel edit"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          </div>
        ) : (
          <>
            <div className="font-medium text-ink">{topic.name}</div>
            <div className="text-sm text-muted-foreground">{topic.description}</div>
            {reconciled && fusesLabel && (
              <div className="mt-1 text-xs text-muted-foreground">Fuses: {fusesLabel}</div>
            )}
          </>
        )}
      </div>

      {!editing && (
        <>
          <button
            onClick={startEdit}
            className="text-muted-foreground hover:text-ink"
            aria-label="Edit topic"
          >
            <Pencil className="h-4 w-4" />
          </button>
          <button
            onClick={() => setConfirmDelete(true)}
            className="text-muted-foreground hover:text-acteu-red"
            aria-label="Delete topic"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </>
      )}

      <Dialog open={confirmDelete} onOpenChange={setConfirmDelete}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete topic</DialogTitle>
            <DialogDescription>
              {reconciled
                ? "This reconciled topic will be split back into its original constituent topics."
                : `"${topic.name}" will be removed from the topic list. This cannot be undone.`}
            </DialogDescription>
          </DialogHeader>
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setConfirmDelete(false)}>
              Cancel
            </Button>
            <Button
              onClick={() => {
                setConfirmDelete(false);
                onDelete();
              }}
            >
              Delete
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </li>
  );
}
