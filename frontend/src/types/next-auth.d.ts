/**
 * Module augmentation that teaches NextAuth about this app's custom fields.
 *
 * The credentials provider (see `lib/auth.ts`) stores the backend bearer token
 * and the user's role/username on the session and JWT; these `declare module`
 * blocks widen NextAuth's built-in `Session`, `User` and `JWT` types so those
 * fields are typed everywhere they are read.
 *
 * @packageDocumentation
 */
import type { UserRole } from "@/types/api";
import "next-auth";
import "next-auth/jwt";

declare module "next-auth" {
  /** The client-visible session, extended with the backend token and user role. */
  interface Session {
    accessToken: string;
    user: {
      id: string;
      username: string;
      role: UserRole;
      name?: string | null;
      email?: string | null;
      image?: string | null;
    };
  }

  /** The user object returned by `authorize()`, carrying the backend token. */
  interface User {
    id: string;
    username: string;
    role: UserRole;
    accessToken: string;
  }
}

declare module "next-auth/jwt" {
  /** The encrypted JWT payload persisted between requests. */
  interface JWT {
    userId: string;
    username: string;
    role: UserRole;
    accessToken: string;
  }
}
