export { default as proxy } from "next-auth/middleware";

export const config = {
  matcher: ["/pipeline/:path*", "/projects/:path*", "/visualizer/:path*"],
};
