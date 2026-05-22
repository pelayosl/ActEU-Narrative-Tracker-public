export { default } from "next-auth/middleware";

// Protect every app section. Unauthenticated users are redirected to /login.
export const config = {
  matcher: ["/pipeline/:path*", "/projects/:path*", "/visualizer/:path*"],
};
