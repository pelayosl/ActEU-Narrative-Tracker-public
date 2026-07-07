/**
 * Root layout wrapping every page in the app.
 *
 * @packageDocumentation
 */
import type { Metadata } from "next";
import { Providers } from "@/components/providers";
import "./globals.css";

/** Static page metadata (title and description) applied site-wide. */
export const metadata: Metadata = {
  title: "ActEU Narrative Tracker",
  description: "Discover, analyse and visualise political narratives across Europe.",
};

/**
 * The `<html>`/`<body>` shell shared by all routes, mounting the global
 * {@link Providers} (React Query, NextAuth session) around the page content.
 *
 * @param props - Component props; `children` is the active route's rendered content.
 */
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
