import type { NextAuthOptions } from "next-auth";
import CredentialsProvider from "next-auth/providers/credentials";
import type { UserRole } from "@/types/api";

// Server-side only — talks to FastAPI directly (no CORS / no proxy).
const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

interface JwtClaims {
  sub: string;
  username: string;
  role: UserRole;
  exp: number;
}

/** Read JWT claims without verifying the signature — the backend re-verifies on every call. */
function decodeJwtClaims(token: string): JwtClaims {
  const part = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
  return JSON.parse(Buffer.from(part, "base64").toString("utf8")) as JwtClaims;
}

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
