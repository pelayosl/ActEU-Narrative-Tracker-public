/**
 * Layout for the authenticated `(app)` route group.
 *
 * @packageDocumentation
 */
import { AppShell } from "@/components/layout/app-shell";
import { AuthGuard } from "@/components/auth/auth-guard";

/**
 * Wrap the protected pages in an {@link AuthGuard} (redirecting unauthenticated
 * users) and the {@link AppShell} chrome (header and sidebar).
 *
 * @param props - Component props; `children` is the active protected route's content.
 */
export default function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthGuard>
      <AppShell>{children}</AppShell>
    </AuthGuard>
  );
}
