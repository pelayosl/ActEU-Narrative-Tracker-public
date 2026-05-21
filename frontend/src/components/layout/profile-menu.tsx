"use client";

import { UserCircle } from "lucide-react";

// TODO: dropdown with "Register user" (admin only) and "Log out".
export function ProfileMenu() {
  return (
    <button className="rounded-full p-1 hover:bg-bg" aria-label="Profile menu">
      <UserCircle className="h-6 w-6 text-ink" />
    </button>
  );
}
