"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useSession } from "next-auth/react";

// Client-side safety net for sessions that expire while the app is open. The
// middleware guards navigation/refresh; this catches an in-app expiry (detected on
// the next session refetch) and forces re-login, blocking the UI so no action can
// run against an expired token.
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
