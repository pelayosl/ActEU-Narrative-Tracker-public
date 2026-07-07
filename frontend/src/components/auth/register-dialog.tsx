/**
 * Admin-only dialog for registering a new user account.
 *
 * @packageDocumentation
 */
"use client";

import { useState } from "react";
import { useSession } from "next-auth/react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PasswordInput } from "@/components/ui/password-input";
import { Label } from "@/components/ui/label";
import { api, isDatabaseUnavailable, DB_UNAVAILABLE_MESSAGE } from "@/lib/api-client";
import type { UserRole } from "@/types/api";

/** Usernames may contain only letters, digits and underscores. */
const USERNAME_RE = /^[A-Za-z0-9_]+$/;

/**
 * Check a password against the strength policy (mirrors the backend rules).
 *
 * @param pw - The candidate password.
 * @returns An error message if invalid, or `null` if the password is acceptable.
 */
function validatePassword(pw: string): string | null {
  if (pw.length < 8) return "Password must be at least 8 characters.";
  if (!/[A-Z]/.test(pw)) return "Password must contain an uppercase letter.";
  if (!/[0-9]/.test(pw)) return "Password must contain a number.";
  return null;
}

/** Blank registration form state. */
const EMPTY = { name: "", surname: "", username: "", password: "", role: "user" as UserRole };

/**
 * Modal form that creates a user via the admin-only register endpoint.
 *
 * Validates the username and password client-side before submitting, and maps
 * backend failures to friendly messages (409 → username taken, 503 → database
 * unavailable). Requires the current admin's bearer token.
 *
 * @param props - Component props: `open` (whether the dialog is visible) and
 *   `onOpenChange` (callback to open/close the dialog).
 */
export function RegisterDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const { data: session } = useSession();
  const [form, setForm] = useState(EMPTY);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);
  const [loading, setLoading] = useState(false);

  function update(field: keyof typeof form, value: string) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSuccess(false);

    if (!USERNAME_RE.test(form.username)) {
      setError("Username cannot contain spaces or special characters.");
      return;
    }
    const pwError = validatePassword(form.password);
    if (pwError) {
      setError(pwError);
      return;
    }

    setLoading(true);
    try {
      await api.register(form, session?.accessToken);
      setSuccess(true);
      setForm(EMPTY);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "";
      setError(
        isDatabaseUnavailable(err)
          ? DB_UNAVAILABLE_MESSAGE
          : msg.includes("409")
            ? "This username is already taken"
            : "Registration failed. Please try again.",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Register a new user</DialogTitle>
          <DialogDescription>Only administrators can create accounts.</DialogDescription>
        </DialogHeader>
        <form onSubmit={onSubmit} className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label htmlFor="reg-name">Name</Label>
              <Input id="reg-name" value={form.name} onChange={(e) => update("name", e.target.value)} required />
            </div>
            <div>
              <Label htmlFor="reg-surname">Surname</Label>
              <Input
                id="reg-surname"
                value={form.surname}
                onChange={(e) => update("surname", e.target.value)}
                required
              />
            </div>
          </div>
          <div>
            <Label htmlFor="reg-username">Username</Label>
            <Input
              id="reg-username"
              value={form.username}
              onChange={(e) => update("username", e.target.value)}
              required
            />
          </div>
          <div>
            <Label htmlFor="reg-password">Password</Label>
            <PasswordInput
              id="reg-password"
              value={form.password}
              onChange={(e) => update("password", e.target.value)}
              required
            />
          </div>
          <div>
            <Label htmlFor="reg-role">Role</Label>
            <select
              id="reg-role"
              value={form.role}
              onChange={(e) => update("role", e.target.value)}
              className="h-10 w-full rounded-md border border-border bg-white px-3 text-sm text-ink outline-none focus:border-acteu-red focus:ring-1 focus:ring-acteu-red"
            >
              <option value="user">User</option>
              <option value="admin">Admin</option>
            </select>
          </div>
          {error && <p className="text-sm text-acteu-red">{error}</p>}
          {success && <p className="text-sm text-green-600">User created successfully.</p>}
          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? "Creating…" : "Create user"}
          </Button>
        </form>
      </DialogContent>
    </Dialog>
  );
}
