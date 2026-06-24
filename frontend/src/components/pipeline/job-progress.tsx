"use client";

// Red progress bar for long-running jobs (BERTopic, reconciliation, training).
// `progress` is 0-100; `step` is the live status message from the job.
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
