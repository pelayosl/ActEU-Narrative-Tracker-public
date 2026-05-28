/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: "standalone",
  // Backend proxy is handled by src/app/api/backend/[...path]/route.ts.
  // A rewrite is not used here because :path* drops trailing slashes,
  // which breaks FastAPI routes defined with `/`.
};

export default nextConfig;
