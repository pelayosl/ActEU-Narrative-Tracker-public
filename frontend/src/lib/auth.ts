/**
 * NextAuth configuration for credential-based login against the FastAPI backend.
 *
 * Server-side only. The credentials provider posts the username/password to the
 * backend's `/auth/login`, decodes the returned JWT for its claims, and stashes
 * the raw bearer token on the NextAuth session so API calls can authenticate.
 *
 * @packageDocumentation
 */
import type { NextAuthOptions } from "next-auth";
import CredentialsProvider from "next-auth/providers/credentials";
import { DB_UNAVAILABLE_ERROR } from "@/lib/api-client";
import type { UserRole } from "@/types/api";

/** Base URL of the FastAPI backend; server-side only (no CORS / no proxy). */
const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

/** The subset of backend JWT claims the frontend reads. */
interface JwtClaims {
  sub: string;
  username: string;
  role: UserRole;
  exp: number;
}

/**
 * Read JWT claims without verifying the signature.
 *
 * Only the payload segment is base64url-decoded; the backend re-verifies the
 * signature on every call, so client-side verification would be redundant.
 *
 * @param token - A compact JWS (`header.payload.signature`).
 * @returns The decoded claims from the token's payload.
 */
function decodeJwtClaims(token: string): JwtClaims {
  const part = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
  return JSON.parse(Buffer.from(part, "base64").toString("utf8")) as JwtClaims;
}

/**
 * NextAuth options: a JWT session (expiring in step with the backend token), a
 * `/login` sign-in page, the credentials provider, and callbacks that copy the
 * backend token and user fields onto the JWT and session.
 */
export const authOptions: NextAuthOptions = {
  session: {
    strategy: "jwt",
    maxAge: 60 * 60, // matches backend JWT_EXPIRATION_MINUTES (60)
  },
  pages: { signIn: "/login" },
  providers: [
    CredentialsProvider({
      name: "credentials",
      credentials: {
        username: { label: "Username", type: "text" },
        password: { label: "Password", type: "password" },
      },
      async authorize(credentials) {
        if (!credentials?.username || !credentials?.password) return null;

        const res = await fetch(`${BACKEND_URL}/auth/login`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            username: credentials.username,
            password: credentials.password,
          }),
        });
        // A thrown error is surfaced to the form as `res.error`; null collapses to
        // the generic "invalid credentials". Distinguish a down database (503) so
        // the user isn't told their credentials are wrong when the DB is simply down.
        if (res.status === 503) throw new Error(DB_UNAVAILABLE_ERROR);
        if (!res.ok) return null; // 401 → invalid credentials

        const { access_token } = (await res.json()) as { access_token: string };
        const claims = decodeJwtClaims(access_token);

        return {
          id: claims.sub,
          username: claims.username,
          role: claims.role,
          accessToken: access_token,
        };
      },
    }),
  ],
  callbacks: {
    async jwt({ token, user }) {
      if (user) {
        token.userId = user.id;
        token.username = user.username;
        token.role = user.role;
        token.accessToken = user.accessToken;
      }
      return token;
    },
    async session({ session, token }) {
      session.accessToken = token.accessToken;
      session.user = {
        ...session.user,
        id: token.userId,
        username: token.username,
        role: token.role,
      };
      return session;
    },
  },
};
