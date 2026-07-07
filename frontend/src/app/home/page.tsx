/**
 * `/home` route: an alias that renders the same public landing page as `/`
 * (accessible whether logged in or out).
 *
 * @packageDocumentation
 */
import { LandingPage } from "@/components/landing/landing-page";

/** The `/home` route component. */
export default function HomePage() {
  return <LandingPage />;
}
