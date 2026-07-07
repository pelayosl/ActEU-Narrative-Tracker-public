/**
 * Animated progress bar for long-running pipeline jobs.
 *
 * @packageDocumentation
 */
"use client";

/**
 * Shimmering red progress bar for long-running jobs (BERTopic, reconciliation,
 * training). Shows the live status message and percentage when available.
 *
 * @param props - Component props: `progress` (0–100 percentage), `step` (live
 *   status message from the job, if any) and `fallback` (message shown when no
 *   `step` has arrived yet).
 */
export function JobProgress({
  progress,
  step,
  fallback,
}: {
  progress: number;
  step?: string;
  fallback: string;
}) {
  return (
    <div className="space-y-3">
      <div className="h-2 w-full overflow-hidden rounded-full bg-bg">
        <div
          className="relative h-full overflow-hidden rounded-full bg-acteu-red transition-all duration-500"
          style={{ width: `${Math.max(progress, 4)}%` }}
        >
          <div className="absolute inset-0 animate-shimmer bg-gradient-to-r from-transparent via-white/40 to-transparent" />
        </div>
      </div>
      <p className="text-sm text-muted-foreground">
        {step || fallback} {progress > 0 && <span className="tabular-nums">· {progress}%</span>}
      </p>
    </div>
  );
}
