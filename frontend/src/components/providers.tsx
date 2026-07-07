/**
 * App-wide client providers: React Query and the NextAuth session.
 *
 * @packageDocumentation
 */
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

/**
 * Guard flag preventing multiple parallel 401s from each firing their own
 * `signOut`. Reset naturally by the full-page redirect that `signOut` triggers.
 */
let signingOut = false;

/**
 * Global React Query error handler: sign the user out on a 401.
 *
 * @param err - The error thrown by a query or mutation.
 */
function handleApiError(err: unknown) {
  if (err instanceof ApiError && err.status === 401 && !signingOut) {
    signingOut = true;
    void signOut({ callbackUrl: "/login?expired=1" });
  }
}

/**
 * Provide a configured React Query client (401s trigger sign-out and are not
 * retried) and a NextAuth {@link SessionProvider} that periodically re-checks
 * the session, so an expiry is detected even while the user is idle.
 *
 * @param props - Component props; `children` is the tree that consumes these contexts.
 */
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
    // Re-check the session periodically (and on window focus) so an expired session
    // is detected even while the user is idle, triggering the AuthGuard redirect.
    <SessionProvider refetchInterval={5 * 60} refetchOnWindowFocus>
      <QueryClientProvider client={client}>{children}</QueryClientProvider>
    </SessionProvider>
  );
}
