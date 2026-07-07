/**
 * NextAuth catch-all API route (`/api/auth/*`).
 *
 * Wires the shared {@link authOptions} into NextAuth's handler and exposes it for
 * both GET and POST, covering sign-in, sign-out, session and callback endpoints.
 *
 * @packageDocumentation
 */
import NextAuth from "next-auth";
import { authOptions } from "@/lib/auth";

/** The NextAuth request handler built from {@link authOptions}. */
const handler = NextAuth(authOptions);

export { handler as GET, handler as POST };
