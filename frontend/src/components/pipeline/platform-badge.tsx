import { cn } from "@/lib/utils";
import type { Platform } from "@/types/api";

// Outlined badge: colour on the border and text, transparent fill.
const PLATFORM_STYLES: Record<Platform | string, string> = {
  twitter: "border-ink text-ink",
  telegram: "border-blue-500 text-blue-500",
  media: "border-green-600 text-green-600",
};

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
