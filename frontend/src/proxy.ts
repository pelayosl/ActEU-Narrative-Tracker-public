/**
 * Route-protection proxy (Next.js 16 "proxy", formerly middleware).
 *
 * Runs server-side on every matched request, so it covers all entry points —
 * typed URL, link, or refresh. Redirects logged-out users away from protected
 * routes and already-authenticated users away from the login page.
 *
 * @packageDocumentation
 */
import { getToken } from "next-auth/jwt";
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

/** Path prefixes that require an authenticated session. */
const PROTECTED_PREFIXES = ["/pipeline", "/projects", "/visualiser"];

/**
 * Gate each request on authentication and redirect where appropriate.
 *
 * `getToken` returns null for missing or expired NextAuth sessions, so an
 * expired session is treated the same as logged-out. Authenticated users hitting
 * `/login` are sent to the pipeline; unauthenticated users hitting a protected
 * route are sent to `/login`. The landing page (`/`, `/home`) stays public.
 *
 * @param req - The incoming request.
 * @returns A redirect response, or `NextResponse.next()` to allow the request.
 */
export async function proxy(req: NextRequest) {
  const { pathname } = req.nextUrl;
  const token = await getToken({ req, secret: process.env.NEXTAUTH_SECRET });
  const isAuthed = Boolean(token);

  // Skip the login page for already-authenticated users. The landing page (/, /home)
  // stays public — it can be viewed whether logged in or out.
  if (isAuthed && pathname === "/login") {
    return NextResponse.redirect(new URL("/pipeline", req.url));
  }

  // Logged-out / expired users can't reach the protected app.
  const isProtected = PROTECTED_PREFIXES.some(
    (p) => pathname === p || pathname.startsWith(`${p}/`),
  );
  if (!isAuthed && isProtected) {
    return NextResponse.redirect(new URL("/login", req.url));
  }

  return NextResponse.next();
}

/** Next.js matcher limiting the proxy to the login and protected routes. */
export const config = {
  matcher: ["/login", "/pipeline/:path*", "/projects/:path*", "/visualiser/:path*"],
};
