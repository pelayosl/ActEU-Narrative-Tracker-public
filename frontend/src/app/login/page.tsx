import { LoginForm } from "@/components/auth/login-form";

type SearchParams = Promise<{ expired?: string }>;

export default async function LoginPage({ searchParams }: { searchParams: SearchParams }) {
  const { expired } = await searchParams;
  const sessionExpired = expired === "1";

  return (
    <main className="flex min-h-screen items-center justify-center bg-bg px-4">
      <div className="w-full max-w-sm rounded-lg border border-border bg-white p-8 shadow-sm">
        <h1 className="mb-6 text-2xl font-semibold text-ink">ActEU Narrative Tracker</h1>
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
