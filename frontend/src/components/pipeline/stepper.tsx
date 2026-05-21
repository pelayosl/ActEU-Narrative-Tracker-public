"use client";

import { cn } from "@/lib/utils";
import type { PipelineStep } from "@/stores/pipeline-store";

const steps: { id: PipelineStep; label: string }[] = [
  { id: "search", label: "Search" },
  { id: "topics", label: "Topic Modelling" },
  { id: "label", label: "Label Dataset" },
];

// Indicative only — non-clickable.
export function Stepper({ currentStep }: { currentStep: PipelineStep }) {
  const currentIdx = steps.findIndex((s) => s.id === currentStep);
  return (
    <ol className="flex items-center gap-3">
      {steps.map((step, idx) => {
        const reached = idx <= currentIdx;
        return (
          <li key={step.id} className="flex items-center gap-2">
            <span
              className={cn(
                "flex h-7 w-7 items-center justify-center rounded-full text-xs font-semibold",
                reached ? "bg-acteu-red text-white" : "bg-bg text-muted-foreground",
              )}
            >
              {idx + 1}
            </span>
            <span className={cn("text-sm font-medium", reached ? "text-ink" : "text-muted-foreground")}>
              {step.label}
            </span>
            {idx < steps.length - 1 && <span className="mx-2 h-px w-8 bg-border" />}
          </li>
        );
      })}
    </ol>
  );
}
