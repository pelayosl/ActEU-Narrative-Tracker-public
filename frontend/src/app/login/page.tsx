import { LoginForm } from "@/components/auth/login-form";

export default function LoginPage() {
  return (
    <main className="flex min-h-screen items-center justify-center bg-bg px-4">
      <div className="w-full max-w-sm rounded-lg border border-border bg-white p-8 shadow-sm">
        <h1 className="mb-6 text-2xl font-semibold text-ink">ActEU Narrative Tracker</h1>
        <LoginForm />
      </div>
    </main>
  );
}
