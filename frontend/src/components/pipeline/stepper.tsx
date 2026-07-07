/**
 * Progress indicator for the three pipeline steps.
 *
 * @packageDocumentation
 */
"use client";

import { cn } from "@/lib/utils";
import type { PipelineStep } from "@/stores/pipeline-store";

/** The ordered pipeline steps and their display labels. */
const steps: { id: PipelineStep; label: string }[] = [
  { id: "search", label: "Search" },
  { id: "topics", label: "Topic Modelling" },
  { id: "label", label: "Label Dataset" },
];

/**
 * Numbered step indicator that highlights the current and completed steps.
 * Indicative only — the steps are not clickable.
 *
 * @param props - Component props; `currentStep` is the step the pipeline is on.
 */
export function Stepper({ currentStep }: { currentStep: PipelineStep }) {
  const currentIdx = steps.findIndex((s) => s.id === currentStep);
  return (
    <ol className="flex flex-wrap items-center gap-y-2 gap-x-3">
      {steps.map((step, idx) => {
        const reached = idx <= currentIdx;
        return (
          <li key={step.id} className="flex items-center gap-2">
            <span
              className={cn(
                "flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-semibold",
                reached ? "bg-acteu-red text-white" : "bg-bg text-muted-foreground",
              )}
            >
              {idx + 1}
            </span>
            <span className={cn("text-sm font-medium", reached ? "text-ink" : "text-muted-foreground")}>
              {step.label}
            </span>
            {idx < steps.length - 1 && <span className="mx-2 hidden h-px w-8 bg-border sm:block" />}
          </li>
        );
      })}
    </ol>
  );
}
