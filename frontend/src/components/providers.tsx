"use client";

import {
  MutationCache,
  QueryCache,
  QueryClient,
  QueryClientProvider,
} from "@tanstack/react-query";
import { SessionProvider, signOut } from "next-auth/react";
import { useState } from "react";
import { ApiError } from "@/lib/api-client";

// Prevents multiple parallel 401s from each firing their own signOut.
// Reset naturally on the full-page redirect that signOut triggers.
let signingOut = false;

function handleApiError(err: unknown) {
  if (err instanceof ApiError && err.status === 401 && !signingOut) {
    signingOut = true;
    void signOut({ callbackUrl: "/login?expired=1" });
  }
}

export function Providers({ children }: { children: React.ReactNode }) {
  const [client] = useState(
    () =>
      new QueryClient({
        queryCache: new QueryCache({ onError: handleApiError }),
        mutationCache: new MutationCache({ onError: handleApiError }),
        defaultOptions: {
          queries: {
            // Don't hammer the API retrying after the token expires.
            retry: (failureCount, error) => {
              if (error instanceof ApiError && error.status === 401) return false;
              return failureCount < 2;
            },
          },
        },
      }),
  );
  return (
    <SessionProvider>
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    </SessionProvider>
  );
}
