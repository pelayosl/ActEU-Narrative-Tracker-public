/**
 * Catch-all proxy route (`/api/backend/*`) from the browser to FastAPI.
 *
 * Replaces a `next.config` rewrite, which would collapse trailing slashes via
 * `:path*`. This handler preserves the path verbatim, forwards `Authorization`
 * headers, and streams the response body — so server-sent events for
 * long-running NLP jobs work through the same origin (no CORS).
 *
 * @packageDocumentation
 */
import { type NextRequest } from "next/server";

/** Base URL of the FastAPI backend the route forwards to (server-side). */
const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

/** Opt out of static optimisation; every proxied request runs on demand. */
export const dynamic = "force-dynamic";
/** Use the Node.js runtime (needed for streaming and header manipulation). */
export const runtime = "nodejs";

/**
 * Forward one request to the backend and stream back the response.
 *
 * Rebuilds the target URL from the catch-all path segments (preserving any
 * trailing slash and query string), strips hop-by-hop / Next-injected headers,
 * omits the body for GET/HEAD, and disables automatic redirect following so the
 * backend's own status codes reach the client unchanged.
 *
 * @param req - The incoming browser request.
 * @param ctx - Route context whose `params.path` holds the catch-all segments.
 * @returns The upstream response, with its status, headers and streamed body.
 */
async function proxy(req: NextRequest, ctx: { params: Promise<{ path: string[] }> }) {
  const url = new URL(req.url);
  const { path } = await ctx.params;
  const trailing = url.pathname.endsWith("/") ? "/" : "";
  const target = `${BACKEND_URL}/${path.join("/")}${trailing}${url.search}`;

  // Strip hop-by-hop / Next-injected headers that would confuse the backend.
  const headers = new Headers(req.headers);
  headers.delete("host");
  headers.delete("content-length");

  const body =
    req.method === "GET" || req.method === "HEAD" ? undefined : await req.arrayBuffer();

  const upstream = await fetch(target, {
    method: req.method,
    headers,
    body,
    redirect: "manual",
  });

  return new Response(upstream.body, {
    status: upstream.status,
    statusText: upstream.statusText,
    headers: upstream.headers,
  });
}

export {
  proxy as GET,
  proxy as POST,
  proxy as PUT,
  proxy as PATCH,
  proxy as DELETE,
  proxy as OPTIONS,
};
