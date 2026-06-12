"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutGrid, FolderKanban, BarChart3 } from "lucide-react";
import { cn } from "@/lib/utils";
import { ProfileMenu } from "./profile-menu";

const items = [
  { href: "/pipeline", label: "Pipeline", icon: LayoutGrid },
  { href: "/projects", label: "Project Library", icon: FolderKanban },
  { href: "/visualiser", label: "Visualiser", icon: BarChart3 },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="flex w-60 flex-col border-r border-border bg-white">
      <div className="flex items-center justify-between p-4">
        <span className="text-lg font-semibold text-acteu-red">ActEU</span>
        <ProfileMenu />
      </div>
      <nav className="flex-1 space-y-1 p-2">
        {items.map(({ href, label, icon: Icon }) => {
          const active = pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                active ? "bg-acteu-red text-white" : "text-ink hover:bg-bg",
              )}
            >
              <Icon className="h-4 w-4" />
              {label}
            </Link>
          );
        })}
      </nav>
    </aside>
  );
}
