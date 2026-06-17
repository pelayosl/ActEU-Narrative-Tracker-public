import { getToken } from "next-auth/jwt";
import { NextResponse } from "next/server";
import type { NextRequest } from "next/server";

// Next 16 "proxy" (formerly middleware). Runs server-side on every matched request,
// so it covers all entry points — typed URL, link, or refresh. getToken returns null
// for missing or expired NextAuth sessions, so expiry is handled like logged-out.

const PROTECTED_PREFIXES = ["/pipeline", "/projects", "/visualiser"];

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

export const config = {
  matcher: ["/login", "/pipeline/:path*", "/projects/:path*", "/visualiser/:path*"],
};
