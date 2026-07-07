/**
 * Primary navigation sidebar with the profile menu docked at the bottom.
 *
 * @packageDocumentation
 */
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutGrid, FolderKanban, BarChart3, PanelLeftClose } from "lucide-react";
import { cn } from "@/lib/utils";
import { useUiStore } from "@/stores/ui-store";
import { ProfileMenu } from "./profile-menu";

/** Top-level navigation destinations shown in the sidebar. */
const items = [
  { href: "/pipeline", label: "Pipeline", icon: LayoutGrid },
  { href: "/projects", label: "Project Library", icon: FolderKanban },
  { href: "/visualiser", label: "Visualiser", icon: BarChart3 },
];

/**
 * Render the navigation links (highlighting the active route), the collapse
 * control and the {@link ProfileMenu}. Returns `null` when collapsed; in narrow
 * mode it floats over the content as an overlay instead of taking column space.
 */
export function Sidebar() {
  const pathname = usePathname();
  const sidebarOpen = useUiStore((s) => s.sidebarOpen);
  const isNarrow = useUiStore((s) => s.isNarrow);
  const toggleSidebar = useUiStore((s) => s.toggleSidebar);

  if (!sidebarOpen) return null;

  return (
    <aside
      className={cn(
        "flex w-60 flex-col border-r border-border bg-white",
        // Pin to the viewport so the profile section at the bottom stays visible
        // regardless of how tall the page content is. When narrow, hover over the
        // content instead of pushing it aside.
        isNarrow ? "fixed inset-y-0 left-0 z-40 shadow-lg" : "sticky top-0 h-screen",
      )}
    >
      <div className="flex items-center justify-between p-4">
        <Link
          href="/home"
          className="text-lg font-semibold text-acteu-red transition-opacity hover:opacity-80"
          aria-label="Go to home page"
        >
          ActEU
        </Link>
        <button
          type="button"
          onClick={toggleSidebar}
          className="rounded-md p-1 text-ink transition-colors hover:bg-bg"
          aria-label="Hide sidebar"
        >
          <PanelLeftClose className="h-5 w-5" />
        </button>
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
      <div className="border-t border-border p-2">
        <ProfileMenu />
      </div>
    </aside>
  );
}
