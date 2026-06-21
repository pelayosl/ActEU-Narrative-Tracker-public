"use client";

import { useState } from "react";
import { useSession, signOut } from "next-auth/react";
import { UserCircle, UserPlus, LogOut } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { RegisterDialog } from "@/components/auth/register-dialog";

export function ProfileMenu() {
  const { data: session } = useSession();
  const [registerOpen, setRegisterOpen] = useState(false);
  const isAdmin = session?.user?.role === "admin";
  const role = session?.user?.role;
  const roleLabel = role ? role.charAt(0).toUpperCase() + role.slice(1) : "";

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger
          className="flex w-full items-center gap-3 rounded-md px-3 py-2 text-left transition-colors hover:bg-bg"
          aria-label="Profile menu"
        >
          <UserCircle className="h-6 w-6 shrink-0 text-ink" />
          <div className="flex min-w-0 flex-col">
            <span className="truncate text-sm font-medium text-ink">
              {session?.user?.username ?? "Account"}
            </span>
            {roleLabel && (
              <span className="truncate text-xs text-muted-foreground">{roleLabel}</span>
            )}
          </div>
        </DropdownMenuTrigger>
        <DropdownMenuContent>
          {session?.user && (
            <>
              <DropdownMenuLabel>
                {session.user.username} ({session.user.role})
              </DropdownMenuLabel>
              <DropdownMenuSeparator />
            </>
          )}
          {isAdmin && (
            <DropdownMenuItem onSelect={() => setRegisterOpen(true)}>
              <UserPlus className="h-4 w-4" /> Register user
            </DropdownMenuItem>
          )}
          <DropdownMenuItem onSelect={() => signOut({ callbackUrl: "/login" })}>
            <LogOut className="h-4 w-4" /> Log out
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
      <RegisterDialog open={registerOpen} onOpenChange={setRegisterOpen} />
    </>
  );
}
