import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

/**
 * Merge Tailwind CSS class names, resolving conflicts.
 *
 * Combines the conditional-class ergonomics of `clsx` (accepts strings, arrays,
 * and objects) with `tailwind-merge`, which de-duplicates conflicting Tailwind
 * utilities so the last one wins (e.g. `cn("p-2", "p-4")` yields `"p-4"`).
 *
 * @param inputs - Class values: strings, arrays, or conditional objects.
 * @returns The merged, conflict-resolved class-name string.
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
