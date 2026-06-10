"use client";

import { useEffect, useState } from "react";
import type { JobStatus } from "@/types/api";

const TERMINAL = new Set(["SUCCESS", "FAILURE", "REVOKED"]);
const BASE_URL = "/api/backend";

export function useJob(jobId: string | null): JobStatus | null {
  const [status, setStatus] = useState<JobStatus | null>(null);

  useEffect(() => {
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
