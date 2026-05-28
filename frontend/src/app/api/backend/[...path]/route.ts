import { type NextRequest } from "next/server";

// Catch-all proxy from the browser to FastAPI. Replaces the next.config rewrite
// because rewrites collapse trailing slashes via :path*. This proxy preserves the
// path verbatim, forwards Authorization headers, and streams the response body
// (so SSE for long-running NLP jobs works through the same origin).

const BACKEND_URL = process.env.BACKEND_URL ?? "http://localhost:8000";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

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
