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

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger className="rounded-full p-1 hover:bg-bg" aria-label="Profile menu">
          <UserCircle className="h-6 w-6 text-ink" />
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
