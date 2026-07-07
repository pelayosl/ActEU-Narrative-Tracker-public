/**
 * Small outlined badge labelling a document's source platform.
 *
 * @packageDocumentation
 */
import { cn } from "@/lib/utils";
import type { Platform } from "@/types/api";

/** Per-platform border/text colour classes (transparent fill). */
const PLATFORM_STYLES: Record<Platform | string, string> = {
  twitter: "border-ink text-ink",
  telegram: "border-blue-700 text-blue-700",
  media: "border-green-800 text-green-800",
};

/**
 * Outlined pill showing a platform name, colour-coded per platform (falling back
 * to a neutral border for unknown values).
 *
 * @param props - Component props; `platform` is the identifier (e.g. `"twitter"`).
 */
export function PlatformBadge({ platform }: { platform: string }) {
  return (
    <span
      className={cn(
        "rounded border bg-transparent px-2 py-0.5 text-xs font-medium uppercase",
        PLATFORM_STYLES[platform] ?? "border-border text-ink",
      )}
    >
      {platform}
    </span>
  );
}
