import { act, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useJob } from "./use-job";
import type { JobStatus } from "@/types/api";

// Minimal controllable EventSource stand-in (jsdom has none).
class FakeEventSource {
  static instances: FakeEventSource[] = [];
  url: string;
  onmessage: ((e: MessageEvent) => void) | null = null;
  onerror: ((e: Event) => void) | null = null;
  closed = false;

  constructor(url: string) {
    this.url = url;
    FakeEventSource.instances.push(this);
  }
  emit(status: JobStatus) {
    this.onmessage?.({ data: JSON.stringify(status) } as MessageEvent);
  }
  close() {
    this.closed = true;
  }
}

beforeEach(() => {
  FakeEventSource.instances = [];
  vi.stubGlobal("EventSource", FakeEventSource as unknown as typeof EventSource);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("useJob", () => {
  it("returns null and opens no stream when jobId is null", () => {
    const { result } = renderHook(() => useJob(null));

    expect(result.current).toBeNull();
    expect(FakeEventSource.instances).toHaveLength(0);
  });

  it("subscribes to the job stream and exposes the latest status", () => {
    const { result } = renderHook(() => useJob("job-1"));
    const es = FakeEventSource.instances[0];

    expect(es.url).toContain("/jobs/job-1/stream");

    act(() => es.emit({ job_id: "job-1", status: "STARTED", progress: 10, result: {} }));

    expect(result.current).toMatchObject({ status: "STARTED", progress: 10 });
  });

  it("closes the stream once a terminal status arrives", () => {
    const { result } = renderHook(() => useJob("job-1"));
    const es = FakeEventSource.instances[0];

    act(() => es.emit({ job_id: "job-1", status: "SUCCESS", progress: 100, result: { ok: true } }));

    expect(result.current?.status).toBe("SUCCESS");
    expect(es.closed).toBe(true);
  });

  it("closes the stream on unmount", () => {
    const { unmount } = renderHook(() => useJob("job-1"));
    const es = FakeEventSource.instances[0];

    unmount();

    expect(es.closed).toBe(true);
  });
});
