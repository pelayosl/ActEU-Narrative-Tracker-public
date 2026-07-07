/**
 * `/login` route: renders the credential login form.
 *
 * @packageDocumentation
 */
import Link from "next/link";
import { LoginForm } from "@/components/auth/login-form";

/** Query string for the login route; `expired=1` flags a timed-out session. */
type SearchParams = Promise<{ expired?: string }>;

/**
 * The login page. Shows a "session expired" notice when redirected here with
 * `?expired=1` (e.g. by the route proxy after the token lapses), then the form.
 *
 * @param props - Route props; `searchParams` is the parsed query string.
 */
export default async function LoginPage({ searchParams }: { searchParams: SearchParams }) {
  const { expired } = await searchParams;
  const sessionExpired = expired === "1";

  return (
    <main className="flex min-h-screen items-center justify-center bg-bg px-4">
      <div className="w-full max-w-sm rounded-lg border border-border bg-white p-8 shadow-sm">
        <h1 className="mb-6 text-2xl font-semibold text-ink">
          <Link href="/" className="inline-block transition-colors hover:text-acteu-red">
            <span className="text-acteu-red">ActEU</span> Narrative Tracker
          </Link>
        </h1>
        {sessionExpired && (
          <div className="mb-4 rounded-md border border-acteu-red bg-acteu-red/5 px-3 py-2 text-sm text-acteu-red">
            Your session has expired. Please log in again.
          </div>
        )}
        <LoginForm />
      </div>
    </main>
  );
}
