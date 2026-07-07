/**
 * Client-side guard that forces re-login when the session expires in-app.
 *
 * @packageDocumentation
 */
"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useSession } from "next-auth/react";

/**
 * Safety net for sessions that expire while the app is open.
 *
 * The route proxy guards navigation and refreshes; this catches an in-app expiry
 * (detected on the next session refetch) and redirects to `/login?expired=1`,
 * rendering nothing once unauthenticated so no action runs against a dead token.
 *
 * @param props - Component props; `children` is the protected UI to render while authenticated.
 */
export function AuthGuard({ children }: { children: React.ReactNode }) {
  const { status } = useSession();
  const router = useRouter();

  useEffect(() => {
    if (status === "unauthenticated") {
      router.replace("/login?expired=1");
    }
  }, [status, router]);

  // Once the session is gone, stop rendering the protected UI entirely. (During the
  // brief "loading" state we still render — middleware already verified the request.)
  if (status === "unauthenticated") return null;

  return <>{children}</>;
}
