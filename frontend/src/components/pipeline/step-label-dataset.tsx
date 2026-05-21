"use client";

import { Button } from "@/components/ui/button";

// TODO: 3a — topic checkboxes + classifier name input + "Train Classifier" (disabled until ≥1 topic + non-empty name).
// 3b — two cards: "Label Retrieved Documents" (Phase 1) and "Label Custom Query" (Phase 2, expands SearchForm).
// After Phase 1: show breakdown table + "Go to Visualizer" button.
export function StepLabelDataset() {
  return (
    <div className="space-y-6">
      <section className="rounded-lg border border-border bg-white p-6">
        <h2 className="mb-2 text-lg font-semibold text-ink">Train Classifier</h2>
        <p className="text-sm text-muted-foreground">Topic selection + classifier name + Train button.</p>
      </section>
      <section className="grid grid-cols-2 gap-4">
        <div className="rounded-lg border border-border bg-white p-6">
          <h3 className="mb-2 font-semibold text-ink">Label Retrieved Documents</h3>
          <p className="mb-4 text-sm text-muted-foreground">Apply topics to the documents from your search.</p>
          <Button>Label</Button>
        </div>
        <div className="rounded-lg border border-border bg-white p-6">
          <h3 className="mb-2 font-semibold text-ink">Label Custom Query</h3>
          <p className="mb-4 text-sm text-muted-foreground">Define a new query for broader labelling.</p>
          <Button variant="outline">Define Query</Button>
        </div>
      </section>
    </div>
  );
}
