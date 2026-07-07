/**
 * React hook for tracking an asynchronous backend job via server-sent events.
 *
 * @packageDocumentation
 */
"use client";

import { useEffect, useState } from "react";
import type { JobStatus } from "@/types/api";

/** Job states after which no further updates arrive and the stream is closed. */
const TERMINAL = new Set(["SUCCESS", "FAILURE", "REVOKED"]);
/** Same-origin base path for the backend proxy (see `lib/api-client.ts`). */
const BASE_URL = "/api/backend";

/**
 * Subscribe to a job's progress stream and expose its latest status.
 *
 * Opens an `EventSource` on the job's `/stream` endpoint and updates state on
 * each message, closing the connection once a terminal status is reached (or on
 * error). Changing `jobId` resets the status first, so a stale terminal result
 * from a previous job is never reused. Passing `null` disables the subscription.
 *
 * @param jobId - The job to track, or `null` to track nothing.
 * @returns The most recent {@link JobStatus}, or `null` before the first event.
 */
export function useJob(jobId: string | null): JobStatus | null {
  const [status, setStatus] = useState<JobStatus | null>(null);

  useEffect(() => {
    // Clear any status carried over from a previous job, so a stale terminal
    // result is never reused when jobId changes (e.g. re-running reconciliation).
    setStatus(null);
    if (!jobId) return;

    const es = new EventSource(`${BASE_URL}/jobs/${jobId}/stream`);

    es.onmessage = (e: MessageEvent) => {
      const data = JSON.parse(e.data as string) as JobStatus;
      setStatus(data);
      if (TERMINAL.has(data.status)) {
        es.close();
      }
    };

    es.onerror = () => {
      es.close();
    };

    return () => es.close();
  }, [jobId]);

  return status;
}
