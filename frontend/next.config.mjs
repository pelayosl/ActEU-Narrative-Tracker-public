/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: "standalone",
  // Backend proxy is handled by src/app/api/backend/[...path]/route.ts.
  // A rewrite is not used here because :path* drops trailing slashes,
  // which breaks FastAPI routes defined with `/`.
  // skipTrailingSlashRedirect stops Next from 308-redirecting `/foo/` → `/foo`
  // before the proxy route handler runs, so the proxy can forward the trailing
  // slash verbatim to FastAPI (which has redirect_slashes=False and registers
  // index endpoints as `/`).
  skipTrailingSlashRedirect: true,
};

export default nextConfig;
