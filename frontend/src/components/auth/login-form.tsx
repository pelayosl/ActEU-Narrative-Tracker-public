"use client";

import { Button } from "@/components/ui/button";

// TODO: wire to api.login + NextAuth. Show inline "Invalid credentials" on error.
export function LoginForm() {
  return (
    <form className="space-y-4">
      <div>
        <label className="mb-1 block text-sm font-medium text-ink">Username</label>
        <input type="text" className="w-full rounded-md border border-border px-3 py-2 text-sm" />
      </div>
      <div>
        <label className="mb-1 block text-sm font-medium text-ink">Password</label>
        <input type="password" className="w-full rounded-md border border-border px-3 py-2 text-sm" />
      </div>
      <Button type="submit" className="w-full">Log in</Button>
    </form>
  );
}
