/**
 * Credential login form for the `/login` page.
 *
 * @packageDocumentation
 */
"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { signIn } from "next-auth/react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PasswordInput } from "@/components/ui/password-input";
import { Label } from "@/components/ui/label";
import { DB_UNAVAILABLE_ERROR, DB_UNAVAILABLE_MESSAGE } from "@/lib/api-client";

/**
 * Username/password form that signs in via NextAuth credentials.
 *
 * On success it navigates to the pipeline; on failure it shows a generic
 * "Invalid credentials" message (never revealing which field was wrong), except
 * for a backend 503 which is surfaced as the database-unavailable message.
 */
export function LoginForm() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    const res = await signIn("credentials", { username, password, redirect: false });

    setLoading(false);
    if (res?.error) {
      // A 503 from the backend is relayed as DB_UNAVAILABLE_ERROR; anything else
      // stays generic — never reveal which field was wrong.
      setError(res.error === DB_UNAVAILABLE_ERROR ? DB_UNAVAILABLE_MESSAGE : "Invalid credentials");
      return;
    }
    router.push("/pipeline");
    router.refresh();
  }

  return (
    <form onSubmit={onSubmit} className="space-y-4">
      <div>
        <Label htmlFor="username">Username</Label>
        <Input
          id="username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          autoComplete="username"
          required
        />
      </div>
      <div>
        <Label htmlFor="password">Password</Label>
        <PasswordInput
          id="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoComplete="current-password"
          required
        />
      </div>
      {error && <p className="text-sm text-acteu-red">{error}</p>}
      <Button type="submit" className="w-full" disabled={loading}>
        {loading ? "Signing in…" : "Log in"}
      </Button>
    </form>
  );
}
