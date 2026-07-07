/**
 * Root route (`/`): renders the public landing page.
 *
 * @packageDocumentation
 */
import { LandingPage } from "@/components/landing/landing-page";

/** The `/` route component. */
export default function Page() {
  return <LandingPage />;
}
