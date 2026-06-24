import "@testing-library/jest-dom/vitest";
import { afterAll, afterEach, beforeAll } from "vitest";
import { cleanup } from "@testing-library/react";

import { server } from "./msw-server";

// api-client calls relative URLs ("/api/backend/..."). undici's fetch (used in the
// node/jsdom test env) cannot resolve relative URLs, so we prepend the jsdom origin.
// Handlers therefore match against `${TEST_ORIGIN}/api/backend/...`.
export const TEST_ORIGIN = "http://localhost";

// MSW: intercept fetch for the whole test run. Unhandled requests error so a test
// never silently hits a real network. Individual tests add handlers via server.use().
beforeAll(() => {
  server.listen({ onUnhandledRequest: "error" });

  // Wrap MSW's (already-patched) fetch so relative URLs are resolved BEFORE they reach
  // the interceptor. Capturing it here — after listen() — means we delegate to MSW
  // rather than bypassing it.
  const patchedFetch = globalThis.fetch;
  globalThis.fetch = ((input: RequestInfo | URL, init?: RequestInit) => {
    if (typeof input === "string" && input.startsWith("/")) {
      return patchedFetch(`${TEST_ORIGIN}${input}`, init);
    }
    return patchedFetch(input, init);
  }) as typeof fetch;
});

afterEach(() => {
  cleanup(); // unmount React trees between tests
  server.resetHandlers();
});
afterAll(() => server.close());
